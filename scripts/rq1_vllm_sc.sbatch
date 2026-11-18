#!/bin/bash
# SC / NLP: serve one pinned local model with vLLM (loopback only).
# Create outputs/logs BEFORE sbatch; Slurm opens its log before this script runs.
#
#   sbatch scripts/rq1_vllm_sc.sbatch <config.json> smoke
#   sbatch scripts/rq1_vllm_sc.sbatch <config.json> fixtures
#   sbatch scripts/rq1_vllm_sc.sbatch <config.json> main60
#
# SEEDS (default "329 330 331") are run concurrently against the same server, each in
# its own output directory; the first seed is the pre-declared primary run. Rerunning
# the same command resumes completed calls. Outputs: $RUNS/<model-key>/<stage>-s<seed>/,
# RUNS defaults to outputs/rq1-v3; use outputs/rq1-v2-sc for the same-GPU v2 control.
# No v3 model call (including smoke) before the preregistration is committed/pushed.
#SBATCH --job-name=rq1-vllm
#SBATCH --account=nlp
#SBATCH --partition=jag-standard
#SBATCH --gres=gpu:rtx6000ada:1
# One 48 GB RTX 6000 Ada; 48 GB host memory leaves headroom for model loading.
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=12:00:00
# Warn the batch shell before the time limit so pipeline runs stop before the server;
# otherwise vLLM aborts in-flight requests and the abort is journaled as a failure.
#SBATCH --signal=B:USR1@180
#SBATCH --output=outputs/logs/%x-%j.out
set -euo pipefail
umask 077

CONFIG=${1:?config path}
STAGE=${2:?smoke, fixtures or main60}
case "$STAGE" in smoke|fixtures|main60) ;; *) echo "unknown stage $STAGE"; exit 2 ;; esac
SEEDS=${SEEDS:-"329 330 331"}
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"
KEY=$(basename "$CONFIG" .json); KEY=${KEY#assessment.}
RUNS=${RUNS:-outputs/rq1-v3}
# Refuse the historical v1/v2 directories, including aliases via ../ or symlinks.
"$PY" - "$ROOT" "$RUNS" "$CONFIG" <<'EOF'
import json, sys
from pathlib import Path
root, runs, config = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
if runs.is_absolute():
    raise SystemExit('RUNS must be relative to the repository')
dest = (root / runs).resolve()
for old in ('outputs/rq1', 'outputs/rq1-v2'):
    if dest.is_relative_to((root / old).resolve()):
        raise SystemExit('Historical outputs are read-only; choose a new RUNS directory')
if json.loads(config.read_text()).get('contract_version') == 'decision-point-v3':
    if not (root / 'outputs/rq1-v3/preregistration.json').is_file():
        raise SystemExit('Missing v3 preregistration; commit and push it before any model call')
EOF
OUT_ROOT="$ROOT/$RUNS/$KEY"
mkdir -p "$ROOT/outputs/logs" && mkdir -m 700 -p "$OUT_ROOT"
SC_SCRATCH=${SC_SCRATCH:-/nlp/scr/yuantian}
export HF_HOME="$SC_SCRATCH/hf"
export XDG_CACHE_HOME="$SC_SCRATCH/.cache"
export TMPDIR="$SC_SCRATCH/tmp"
mkdir -p "$XDG_CACHE_HOME" "$TMPDIR"
# Retain every attempt's stdout, including resumes/requeues.
ATTEMPT="${SLURM_JOB_ID:-local}-r${SLURM_RESTART_COUNT:-0}-$(date -u +%Y%m%dT%H%M%S)-$$"

# model_id is "<repo>@<revision>"; the server's model name must equal it exactly.
MODEL_ID=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["model"]["model_id"])' "$CONFIG")
REPO=${MODEL_ID%@*}; REVISION=${MODEL_ID#*@}
PORT=$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
export HF_HUB_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
# FlashInfer's fused sampler JIT-compiles with nvcc, which the GPU nodes lack. vLLM
# never uses it for requests with an explicit seed (all of ours), only in warmup.
export VLLM_USE_FLASHINFER_SAMPLER=0
export TUTOR_ASSESSMENT_LOCAL_URL="http://127.0.0.1:$PORT/v1/chat/completions"

echo "host=$(hostname) job=${SLURM_JOB_ID:-none} model=$MODEL_ID stage=$STAGE seeds=$SEEDS"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
"$ROOT/.venv/bin/vllm" serve "$REPO" --revision "$REVISION" --served-model-name "$MODEL_ID" \
    --host 127.0.0.1 --port "$PORT" --max-model-len 131072 --reasoning-parser qwen3 \
    --language-model-only --gpu-memory-utilization 0.92 --max-num-seqs 4 --seed 0 \
    > "$ROOT/outputs/logs/vllm-$KEY-$ATTEMPT.log" 2>&1 &
SERVER=$!
cleanup_server() {
    local status=$?
    kill "$SERVER" 2>/dev/null || true
    wait "$SERVER" 2>/dev/null || true
    exit "$status"
}
trap cleanup_server EXIT
for _ in $(seq 240); do
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $SERVER 2>/dev/null || { echo "vLLM exited during startup"; exit 1; }
    sleep 10
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "vLLM not healthy after 40 min"; exit 1; }
echo "server ready on port $PORT"

seed_config() {  # Same config with only the seed replaced; written next to the runs.
    local path="$OUT_ROOT/config.s$1.json"
    "$PY" - "$CONFIG" "$1" "$path" <<'EOF' || return $?
import json, sys
from pathlib import Path
c = json.loads(Path(sys.argv[1]).read_text()); c['seed'] = int(sys.argv[2])
p = Path(sys.argv[3])
if p.exists():
    if json.loads(p.read_text()) != c:
        raise SystemExit('Seed config changed; use a new RUNS directory')
else:
    with p.open('x') as f:
        json.dump(c, f, indent=2)
EOF
    echo "$path"
}

run_items() {  # <items> <output> <config>; a run with failed items exits 1 but is kept.
    mkdir -m 700 -p "$2"
    local log="$ROOT/outputs/logs/run-$KEY-$STAGE-$(basename "$2")-$ATTEMPT.json"
    local status=0
    TUTOR_ASSESSMENT_TRACE_LOG="$2/trace.jsonl" "$ROOT/.venv/bin/tutor-assess" run \
        --items "$1" --config "$3" --output "$2" > "$log" || status=$?
    echo "== $2 exit=$status"; cat "$log"
    case "$status" in 0|1) ;; *) return "$status" ;; esac
    # Exit 1 may be a recorded invalid model output; never repair or resample it.
    # A crash, stale lock or frozen-input mismatch must not masquerade as completion.
    "$PY" - "$2" <<'EOF'
import sys
from adaptive_tutor.rq1.pipeline import audit_run
frozen, results = audit_run(sys.argv[1])
if len(results) != len(frozen['items']):
    raise SystemExit('Run incomplete; inspect attempt log and Slurm state')
EOF
}

case "$STAGE" in
smoke)
    # Operational check only (JSON/quote validity, long-context memory, latency).
    # The long item is filler text sized like the largest Main 1 item; no human labels.
    ITEMS="$OUT_ROOT/smoke-items.jsonl"
    "$PY" - "$ITEMS" "$ROOT/examples/assessment_items.synthetic.jsonl" <<'EOF'
import json, sys
from pathlib import Path
filler = "\n".join(f"[{i:05d}] build step completed; wrote module_{i % 97}.py ({i * 37 % 1000} lines)" for i in range(2100))
messages = [{"turn_id": "u1", "role": "user", "content": "Refactor the parser and report how many tests pass."},
            {"turn_id": "t2", "role": "tool", "content": filler},
            {"turn_id": "a3", "role": "assistant", "content": "Done. All 214 tests pass and coverage rose from 61% to 78%."},
            {"turn_id": "u4", "role": "user", "content": "Thanks, now write the release notes."}]
item = {"item_id": "synthetic-long-b3", "session_id": "synthetic-session-long", "participant_id": "synthetic-participant-long",
        "agent": "synthetic", "behavior": "B3", "target_turn_id": "u4", "messages": messages}
text = Path(sys.argv[2]).read_text() + json.dumps(item) + '\n'
p = Path(sys.argv[1])
if p.exists():
    if p.read_text() != text:
        raise SystemExit('Smoke items changed; use a new RUNS directory')
else:
    with p.open('x') as f:
        f.write(text)
EOF
    CONFIG329=$(seed_config 329)
    run_items "$ITEMS" "$OUT_ROOT/smoke-s329" "$CONFIG329"
    ;;
main60|fixtures)
    if [ "$STAGE" = main60 ]; then
        DATA="$ROOT/data/rq1/main60"
        REFS="A:independent-human B:independent-human adjudicated:adjudicated"
    else
        DATA="$ROOT/data/rq2/v02_fixtures"
        REFS="fixtures:synthetic-fixture"
    fi
    PIDS=()
    stop_runs() {  # Resume later with the same command; unfinished calls are retried.
        echo "time limit near: stopping pipeline runs before the server"
        local stopped=()
        for pid in "${PIDS[@]}"; do stopped+=($(pgrep -P "$pid")); done
        kill -TERM "${stopped[@]}" 2>/dev/null || true
        wait "${PIDS[@]}" || true
        # SIGTERM skips RunLock cleanup. Release only locks held by the runs stopped
        # here, never one left by another writer.
        for seed in $SEEDS; do
            lock="$OUT_ROOT/$STAGE-s$seed/.run.lock"
            if [ -f "$lock" ] && printf '%s\n' "${stopped[@]}" | grep -qxF "$(cat "$lock")"; then rm -f "$lock"; fi
        done
        exit 0
    }
    trap stop_runs USR1
    for seed in $SEEDS; do
        CURRENT_CONFIG=$(seed_config "$seed")
        run_items "$DATA/items.jsonl" "$OUT_ROOT/$STAGE-s$seed" "$CURRENT_CONFIG" &
        PIDS+=($!)
    done
    status=0
    for pid in "${PIDS[@]}"; do wait "$pid" || status=1; done
    [ "$status" -eq 0 ] || exit "$status"
    for seed in $SEEDS; do
        run="$OUT_ROOT/$STAGE-s$seed"
        for ref in $REFS; do
            reference="$DATA/reference_${ref%%:*}.csv"
            [ "$STAGE" != fixtures ] || reference="$DATA/reference.csv"
            result="$run/vs-${ref%%:*}.json"
            [ ! -e "$result" ] || continue
            "$ROOT/.venv/bin/tutor-assess" evaluate --run "$run" --reference "$reference" \
                --reference-provenance "${ref#*:}" --save "$result" > /dev/null
        done
    done
    ;;
*) echo "unknown stage $STAGE"; exit 2 ;;
esac
echo "stage $STAGE finished"
