#!/bin/bash
# RQ2 live simulation pilot on FarmShare: four pinned local models on one 4x L40S node.
# Create outputs/logs BEFORE sbatch; Slurm opens its log before this script runs.
#
#   mkdir -p outputs/logs && sbatch scripts/rq2_pilot.sbatch [configs/rq2-pilot/pilot.json]
#
# GPU0 assessor (frozen v2 Qwen3.8-27B-FP8, the exact RQ1 server arguments), GPU1 learner,
# GPU2 coach, GPU3 evaluator; every server listens on 127.0.0.1 only. Stages:
#   1. smoke: one complete block (first profile and pair of the config, AB); a failed branch stops the job.
#      In parallel: the v2 assessor and the evaluator on the 13 v0.2 fixtures and on the
#      5 learner-view-v2 fixtures (data/rq2/task_v2_fixtures).
#   2. pilot: the config split into one shard per profile x pair, run concurrently.
#   3. audit every run and write outputs/rq2-pilot/report.md (scripts/rq2_pilot_report.py).
# Rerunning the same command resumes: completed calls, branches and scores are reused.
# New model weights and caches live under /scratch/users/$USER, not $HOME (see ASSESSOR_HUB/MODEL_HUB
# below to run elsewhere; on another cluster also pass its sbatch --account/--partition/--gres).
#SBATCH --job-name=rq2-pilot
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
# Memory is capped at 4000 MB per CPU on this partition; 16 CPUs give 64 GB host RAM
# for four model loads, and leave a CPU each for the servers and the 12 runners.
#SBATCH --cpus-per-task=16
#SBATCH --mem=64000M
#SBATCH --time=04:00:00
# Stop the runners before the servers at the time limit; otherwise vLLM aborts
# in-flight requests and the abort is journaled as a failure.
#SBATCH --signal=B:USR1@300
#SBATCH --output=outputs/logs/%x-%j.out
set -euo pipefail
umask 077

CONFIG=${1:-configs/rq2-pilot/pilot.json}
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"
RUNS="$ROOT/${RUNS:-outputs/rq2-pilot}"
SCRATCH=${SCRATCH_DIR:-/scratch/users/$USER}
# Model caches (scripts/rq2_download_models.sh uses the same defaults). On another cluster set
# SCRATCH_DIR, and ASSESSOR_HUB / MODEL_HUB if the weights live elsewhere (one hub for all is fine).
ASSESSOR_HUB=${ASSESSOR_HUB:-$HOME/.cache/huggingface/hub}
MODEL_HUB=${MODEL_HUB:-$SCRATCH/hf/hub}
mkdir -p "$ROOT/outputs/logs" && mkdir -m 700 -p "$RUNS"
[ -f "$CONFIG" ] || { echo "missing $CONFIG"; exit 2; }

export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}" HF_HUB_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
# Compile/kernel caches on scratch, not $HOME (HF_HOME is pinned above, so this does
# not move the frozen Qwen weights).
export XDG_CACHE_HOME="$SCRATCH/cache" VLLM_CACHE_ROOT="$SCRATCH/cache/vllm" \
       TRITON_CACHE_DIR="$SCRATCH/cache/triton" PIP_CACHE_DIR="$SCRATCH/cache/pip"
# FlashInfer's fused sampler JIT-compiles with nvcc, which the GPU nodes lack.
export VLLM_USE_FLASHINFER_SAMPLER=0
ATTEMPT="${SLURM_JOB_ID:-local}-r${SLURM_RESTART_COUNT:-0}-$(date -u +%Y%m%dT%H%M%S)"
echo "host=$(hostname) job=${SLURM_JOB_ID:-none} config=$CONFIG runs=$RUNS attempt=$ATTEMPT"
nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv,noheader

model_id() { "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"][sys.argv[2]]["model_id"])' "$CONFIG" "$1"; }
free_port() { "$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }

declare -A PORT SERVER
serve() {  # <role> <gpu> <hf hub cache> [extra vllm args...]; served name must equal model_id
    local role=$1 gpu=$2 cache=$3; shift 3
    local id; id=$(model_id "$role")
    PORT[$role]=$(free_port)
    CUDA_VISIBLE_DEVICES=$gpu HF_HUB_CACHE=$cache "$ROOT/.venv/bin/vllm" serve "${id%@*}" --revision "${id#*@}" \
        --served-model-name "$id" --host 127.0.0.1 --port "${PORT[$role]}" --seed 0 "$@" \
        > "$ROOT/outputs/logs/vllm-$role-$ATTEMPT.log" 2>&1 &
    SERVER[$role]=$!
    export "TUTOR_${role^^}_LOCAL_URL=http://127.0.0.1:${PORT[$role]}/v1/chat/completions"
    echo "$role: $id on GPU $gpu port ${PORT[$role]}"
}
cleanup() {
    local status=$?
    kill "${SERVER[@]}" 2>/dev/null || true
    wait "${SERVER[@]}" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT

# Assessor: unchanged from scripts/rq1_vllm.sbatch / rq1_vllm_sc.sbatch.
serve assessment 0 "$ASSESSOR_HUB" --max-model-len 131072 --reasoning-parser qwen3 \
    --language-model-only --gpu-memory-utilization 0.92 --max-num-seqs 4
serve learner 1 "$MODEL_HUB" --max-model-len 32768 --language-model-only \
    --gpu-memory-utilization 0.90 --max-num-seqs 16
# The repo ships both formats; only the HF weights are downloaded (config.json, model-*.safetensors),
# so pin them: "auto" would pick Mistral format from params.json and look for consolidated.safetensors.
# The tokenizer is Mistral's own (tekken.json): this repo's HF tokenizer.json has the known
# pre-tokenizer regex bug (transformers asks for fix_mistral_regex=True, which vLLM never sets).
serve coach 2 "$MODEL_HUB" --max-model-len 32768 --language-model-only \
    --gpu-memory-utilization 0.90 --max-num-seqs 16 \
    --tokenizer-mode mistral --config-format hf --load-format safetensors \
    --structured-outputs-config '{"disable_any_whitespace": true}'
serve evaluator 3 "$MODEL_HUB" --max-model-len 65536 --reasoning-parser openai_gptoss \
    --gpu-memory-utilization 0.90 --max-num-seqs 16

for role in assessment learner coach evaluator; do
    for _ in $(seq 240); do
        curl -sf "http://127.0.0.1:${PORT[$role]}/health" >/dev/null && break
        kill -0 "${SERVER[$role]}" 2>/dev/null || { echo "vLLM $role exited during startup; see outputs/logs/vllm-$role-$ATTEMPT.log"; exit 1; }
        sleep 10
    done
    curl -sf "http://127.0.0.1:${PORT[$role]}/health" >/dev/null || { echo "vLLM $role not healthy after 40 min"; exit 1; }
    echo "$role server ready"
done

shard_config() {  # <out dir> <json overrides>; written once next to the run, never changed
    "$PY" - "$CONFIG" "$1/config.json" "$2" <<'EOF'
import json, sys
from pathlib import Path
c = json.loads(Path(sys.argv[1]).read_text()); c.update(json.loads(sys.argv[3]))
p = Path(sys.argv[2]); p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
if p.exists():
    if json.loads(p.read_text()) != c:
        raise SystemExit(f'{p} changed; use a new RUNS directory')
else:
    with p.open('x') as f:
        json.dump(c, f, indent=2)
EOF
}

PIDS=()
RUN_DIRS=()
start_run() {  # <out dir>: the backgrounded process is the runner itself, so $! owns .run.lock
    local out=$1
    TUTOR_ASSESSMENT_TRACE_LOG="$out/trace-assessment.jsonl" TUTOR_EVALUATOR_TRACE_LOG="$out/trace-evaluator.jsonl" \
    TUTOR_LEARNER_TRACE_LOG="$out/trace-learner.jsonl" TUTOR_COACH_TRACE_LOG="$out/trace-coach.jsonl" \
        "$PY" -m adaptive_tutor run --config "$out/config.json" --output "$out" > "$out/run-$ATTEMPT.json" 2> "$out/run-$ATTEMPT.err" &
    PIDS+=($!)
    RUN_DIRS+=("$out")
}
stop_runs() {  # Resume later with the same command; unfinished calls are retried.
    echo "time limit near: stopping runners before the servers"
    # Never a bare `wait`: with no PIDs it would block on the vLLM servers.
    [ "${#PIDS[@]}" -gt 0 ] || exit 0
    kill -TERM "${PIDS[@]}" 2>/dev/null || true
    wait "${PIDS[@]}" 2>/dev/null || true
    # SIGTERM skips RunLock cleanup. Release only locks held by the runners stopped here.
    local i
    for i in "${!PIDS[@]}"; do
        lock="${RUN_DIRS[$i]}/.run.lock"
        if [ -f "$lock" ] && [ "$(cat "$lock")" = "${PIDS[$i]}" ]; then rm -f "$lock"; fi
    done
    exit 0
}
trap stop_runs USR1

fixtures() {  # <name> <tutor-assess config> <role whose server answers> [fixture dir under data/rq2]
    local out="$RUNS/fixtures-$1-s329" data="$ROOT/data/rq2/${4:-v02_fixtures}"
    mkdir -m 700 -p "$out"
    local status=0
    TUTOR_ASSESSMENT_LOCAL_URL="http://127.0.0.1:${PORT[$3]}/v1/chat/completions" TUTOR_ASSESSMENT_TRACE_LOG="$out/trace.jsonl" \
        "$ROOT/.venv/bin/tutor-assess" run --items "$data/items.jsonl" --config "$2" --output "$out" \
        > "$out/run-$ATTEMPT.json" 2>&1 || status=$?
    echo "== fixtures $1 exit=$status"
    "$ROOT/.venv/bin/tutor-assess" evaluate --run "$out" --reference "$data/reference.csv" \
        --reference-provenance synthetic-fixture --save "$out/vs-fixtures.json" > /dev/null || true
}

# Stage 1: smoke block (must be clean) alongside the fixture checks.
SMOKE="$RUNS/smoke"
# The config's first profile and pair (pilot: novice_a, briefs_01), so a test-split config works too.
SMOKE_SET=$("$PY" -c 'import json,sys; c=json.load(open(sys.argv[1])); print(json.dumps({"profiles": c["profiles"][:1], "pairs": c["pairs"][:1], "orientations": ["AB"], "replicates": 1}))' "$CONFIG")
shard_config "$SMOKE" "$SMOKE_SET"
fixtures assessor-v2-qwen38-27b "$ROOT/configs/v2/assessment.qwen38-27b-fp8.json" assessment &
FIX1=$!
fixtures evaluator-gpt-oss-20b "$ROOT/configs/rq2-pilot/evaluator.gpt-oss-20b.json" evaluator &
FIX2=$!
# Learner view v2 (goal only, no table name): does B2 now use the 0/1/2 range?
fixtures taskv2-assessor-v2-qwen38-27b "$ROOT/configs/v2/assessment.qwen38-27b-fp8.json" assessment task_v2_fixtures &
FIX3=$!
fixtures taskv2-evaluator-gpt-oss-20b "$ROOT/configs/rq2-pilot/evaluator.gpt-oss-20b.json" evaluator task_v2_fixtures &
FIX4=$!
start_run "$SMOKE"
smoke_status=0
wait "${PIDS[0]}" || smoke_status=$?
PIDS=(); RUN_DIRS=()
echo "== smoke exit=$smoke_status"; cat "$SMOKE/run-$ATTEMPT.json" || true
# Gate on the dialogue itself (learner, assessor, coach): a failed branch stops the job.
# Failed scores (evaluator only) do not: the learner transcripts, the pilot's main output,
# do not depend on them, and blinded packets can be rescored later.
gate=$("$PY" - "$SMOKE/manifest.json" <<'EOF'
import json, sys
try:
    m = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    print("crashed"); raise SystemExit
print("branches" if m["failed_branches"] else "scores" if m["failed_scores"] else "ok")
EOF
)
if [ "$gate" = crashed ] || [ "$gate" = branches ]; then
    echo "smoke block failed ($gate); not starting the pilot. Inspect $SMOKE (events.jsonl, run-*.err, trace-*.jsonl)."
    tail -n 20 "$SMOKE/run-$ATTEMPT.err" || true
    wait $FIX1 $FIX2 $FIX3 $FIX4 || true
    exit 1
fi
[ "$gate" = ok ] || echo "WARNING: smoke evaluator scores failed; continuing for learner transcripts. Inspect $SMOKE/trace-evaluator.jsonl."

# Stage 2: one shard per profile x pair, concurrently.
read -r -a PROFILES <<< "$("$PY" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["profiles"]))' "$CONFIG")"
read -r -a PAIRS <<< "$("$PY" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["pairs"]))' "$CONFIG")"
for profile in "${PROFILES[@]}"; do
    for pair in "${PAIRS[@]}"; do
        out="$RUNS/shards/$profile.$pair"
        shard_config "$out" "{\"profiles\": [\"$profile\"], \"pairs\": [\"$pair\"]}"
        start_run "$out"
    done
done
echo "started ${#PIDS[@]} shards"
status=0
for pid in "${PIDS[@]}"; do wait "$pid" || status=1; done
wait $FIX1 $FIX2 $FIX3 $FIX4 || true

# Stage 3: audit and report (also runnable later on a login node).
for out in "$SMOKE" "$RUNS"/shards/*; do
    "$PY" -m adaptive_tutor audit --output "$out" > "$out/audit.json" 2>&1 || echo "audit failed: $out"
done
"$PY" "$ROOT/scripts/rq2_pilot_report.py" "$RUNS" || echo "report failed"
echo "pilot finished (runner status $status)"
