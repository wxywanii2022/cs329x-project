#!/bin/bash
# Serve one pinned local model with vLLM (loopback only) and run tutor-assess against it.
#
#   sbatch scripts/rq1_vllm.sbatch <config.json> smoke    # synthetic items + one long synthetic item
#   sbatch scripts/rq1_vllm.sbatch <config.json> main60   # Main 1 for each seed in SEEDS, then evaluate
#
# SEEDS (default "329 330 331") are run concurrently against the same server, each in
# its own output directory; the first seed is the pre-declared primary run. Rerunning
# the same command resumes completed calls. Outputs: $RUNS/<model-key>/<stage>-s<seed>/,
# RUNS defaulting to outputs/rq1 (protocol v1); use RUNS=outputs/rq1-v2 with configs/v2/.
#SBATCH --job-name=rq1-vllm
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
# Small CPU/memory requests start much sooner: GPU nodes often have free GPUs but
# few free CPUs, and memory is capped at 4000 MB per CPU.
#SBATCH --cpus-per-task=6
#SBATCH --mem=23400M
#SBATCH --time=12:00:00
# Warn the batch shell before the time limit so pipeline runs stop before the server;
# otherwise vLLM aborts in-flight requests and the abort is journaled as a failure.
#SBATCH --signal=B:USR1@180
#SBATCH --output=outputs/logs/%x-%j.out
set -euo pipefail

CONFIG=${1:?config path}
STAGE=${2:?smoke or main60}
SEEDS=${SEEDS:-"329 330 331"}
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"
KEY=$(basename "$CONFIG" .json); KEY=${KEY#assessment.}
OUT_ROOT="$ROOT/${RUNS:-outputs/rq1}/$KEY"
mkdir -p "$ROOT/outputs/logs" && mkdir -m 700 -p "$OUT_ROOT"

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
    > "$ROOT/outputs/logs/vllm-$KEY-${SLURM_JOB_ID:-local}.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; wait $SERVER 2>/dev/null' EXIT
for _ in $(seq 240); do
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $SERVER 2>/dev/null || { echo "vLLM exited during startup"; exit 1; }
    sleep 10
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "vLLM not healthy after 40 min"; exit 1; }
echo "server ready on port $PORT"

seed_config() {  # Same config with only the seed replaced; written next to the runs.
    local path="$OUT_ROOT/config.s$1.json"
    "$PY" -c 'import json,sys; c=json.load(open(sys.argv[1])); c["seed"]=int(sys.argv[2]); json.dump(c, open(sys.argv[3], "w"), indent=2)' "$CONFIG" "$1" "$path"
    echo "$path"
}

run_items() {  # <items> <output> <config>; a run with failed items exits 1 but is kept.
    mkdir -m 700 -p "$2"
    TUTOR_ASSESSMENT_TRACE_LOG="$2/trace.jsonl" "$ROOT/.venv/bin/tutor-assess" run \
        --items "$1" --config "$3" --output "$2" > "$2/run.stdout.json" || true
    echo "== $2"; cat "$2/run.stdout.json"
}

case "$STAGE" in
smoke)
    # Operational check only (JSON/quote validity, long-context memory, latency).
    # The long item is filler text sized like the largest Main 1 item; no human labels.
    ITEMS="$OUT_ROOT/smoke-items.jsonl"
    cp "$ROOT/examples/assessment_items.synthetic.jsonl" "$ITEMS"
    "$PY" - "$ITEMS" <<'EOF'
import json, sys
filler = "\n".join(f"[{i:05d}] build step completed; wrote module_{i % 97}.py ({i * 37 % 1000} lines)" for i in range(2100))
messages = [{"turn_id": "u1", "role": "user", "content": "Refactor the parser and report how many tests pass."},
            {"turn_id": "t2", "role": "tool", "content": filler},
            {"turn_id": "a3", "role": "assistant", "content": "Done. All 214 tests pass and coverage rose from 61% to 78%."},
            {"turn_id": "u4", "role": "user", "content": "Thanks, now write the release notes."}]
item = {"item_id": "synthetic-long-b3", "session_id": "synthetic-session-long", "participant_id": "synthetic-participant-long",
        "agent": "synthetic", "behavior": "B3", "target_turn_id": "u4", "messages": messages}
open(sys.argv[1], "a", encoding="utf-8").write(json.dumps(item) + "\n")
EOF
    run_items "$ITEMS" "$OUT_ROOT/smoke-s329" "$(seed_config 329)"
    ;;
main60)
    DATA="$ROOT/data/rq1/main60"
    PIDS=()
    stop_runs() {  # Resume later with the same command; unfinished calls are retried.
        echo "time limit near: stopping pipeline runs before the server"
        local stopped=()
        for pid in "${PIDS[@]}"; do stopped+=($(pgrep -P "$pid")); done
        kill -TERM "${stopped[@]}" 2>/dev/null || true
        wait "${PIDS[@]}"
        # SIGTERM skips RunLock cleanup. Release only locks held by the runs stopped
        # here, never one left by another writer.
        for seed in $SEEDS; do
            lock="$OUT_ROOT/main60-s$seed/.run.lock"
            if [ -f "$lock" ] && printf '%s\n' "${stopped[@]}" | grep -qxF "$(cat "$lock")"; then rm -f "$lock"; fi
        done
        exit 0
    }
    trap stop_runs USR1
    for seed in $SEEDS; do
        run_items "$DATA/items.jsonl" "$OUT_ROOT/main60-s$seed" "$(seed_config "$seed")" &
        PIDS+=($!)
    done
    wait "${PIDS[@]}"  # not bare wait: that would also block on the vLLM server
    for seed in $SEEDS; do
        run="$OUT_ROOT/main60-s$seed"
        for ref in A:independent-human B:independent-human adjudicated:adjudicated; do
            "$ROOT/.venv/bin/tutor-assess" evaluate --run "$run" --reference "$DATA/reference_${ref%%:*}.csv" \
                --reference-provenance "${ref#*:}" --save "$run/vs-${ref%%:*}.json" > /dev/null || true
        done
    done
    ;;
*) echo "unknown stage $STAGE"; exit 2 ;;
esac
echo "stage $STAGE finished"
