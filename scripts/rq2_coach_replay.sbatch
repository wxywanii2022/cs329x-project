#!/bin/bash
# Replay pilot coach decisions with a new coach prompt on one GPU (coach server only).
#
#   mkdir -p outputs/logs && sbatch scripts/rq2_coach_replay.sbatch [pilot dir] [output dir] [prompt]
#
# Defaults: outputs/rq2-pilot, outputs/rq2-coach-replay, src/adaptive_tutor/prompts/coach_v2.txt.
# Rerunning resumes (finished call IDs are skipped). Server flags match scripts/rq2_pilot.sbatch.
#SBATCH --job-name=rq2-coach-replay
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32000M
#SBATCH --time=01:00:00
#SBATCH --output=outputs/logs/%x-%j.out
set -euo pipefail
umask 077

PILOT=${1:-outputs/rq2-pilot}
OUT=${2:-outputs/rq2-coach-replay}
PROMPT=${3:-src/adaptive_tutor/prompts/coach_v2.txt}
CONFIG=configs/rq2-pilot/pilot.json
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"
SCRATCH=${SCRATCH_DIR:-/scratch/users/$USER}
MODEL_HUB=${MODEL_HUB:-$SCRATCH/hf/hub}
mkdir -p "$ROOT/outputs/logs" && mkdir -m 700 -p "$OUT"

export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}" HF_HUB_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export XDG_CACHE_HOME="$SCRATCH/cache" VLLM_CACHE_ROOT="$SCRATCH/cache/vllm" \
       TRITON_CACHE_DIR="$SCRATCH/cache/triton" PIP_CACHE_DIR="$SCRATCH/cache/pip"
export VLLM_USE_FLASHINFER_SAMPLER=0
echo "host=$(hostname) job=${SLURM_JOB_ID:-none} pilot=$PILOT out=$OUT prompt=$PROMPT"

ID=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"]["coach"]["model_id"])' "$CONFIG")
PORT=$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
CUDA_VISIBLE_DEVICES=0 HF_HUB_CACHE="$MODEL_HUB" "$ROOT/.venv/bin/vllm" serve "${ID%@*}" --revision "${ID#*@}" \
    --served-model-name "$ID" --host 127.0.0.1 --port "$PORT" --seed 0 --max-model-len 32768 \
    --language-model-only --gpu-memory-utilization 0.90 --max-num-seqs 16 \
    --tokenizer-mode mistral --config-format hf --load-format safetensors \
    --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' \
    > "$ROOT/outputs/logs/vllm-coach-replay-${SLURM_JOB_ID:-local}.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true; wait $SERVER 2>/dev/null || true' EXIT
export TUTOR_COACH_LOCAL_URL="http://127.0.0.1:$PORT/v1/chat/completions" TUTOR_COACH_TRACE_LOG="$OUT/trace-coach.jsonl"

for _ in $(seq 180); do
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $SERVER 2>/dev/null || { echo "coach server exited during startup"; exit 1; }
    sleep 10
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "coach server not healthy"; exit 1; }
echo "coach server ready"

# REPLAY_ARGS adds flags, e.g. REPLAY_ARGS=--no-gap for the full-coach no-gap check.
"$PY" scripts/rq2_coach_replay.py --pilot "$PILOT" --output "$OUT" --prompt "$PROMPT" --config "$CONFIG" ${REPLAY_ARGS:-}
