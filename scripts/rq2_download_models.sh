#!/bin/bash
# Download the four RQ2 models at the revisions pinned in the config (about 75 GB in total).
# Run once on a node with internet access, before sbatch; the job itself runs offline.
#
#   bash scripts/rq2_download_models.sh [configs/rq2-pilot/pilot.json]
#
# Same locations as scripts/rq2_pilot.sbatch (override both scripts the same way):
#   ASSESSOR_HUB  Qwen3.8-27B-FP8 cache   (default ~/.cache/huggingface/hub, 25 GB)
#   MODEL_HUB     learner, coach, evaluator (default $SCRATCH_DIR/hf/hub, 22 + 15 + 13 GB;
#                 SCRATCH_DIR defaults to /scratch/users/$USER)
# The repos are ungated, so no token is needed. Rerunning skips files already present.
set -euo pipefail
CONFIG=${1:-configs/rq2-pilot/pilot.json}
HF=${HF:-.venv/bin/hf}
SCRATCH=${SCRATCH_DIR:-/scratch/users/$USER}
ASSESSOR_HUB=${ASSESSOR_HUB:-$HOME/.cache/huggingface/hub}
MODEL_HUB=${MODEL_HUB:-$SCRATCH/hf/hub}
mkdir -p "$ASSESSOR_HUB" "$MODEL_HUB"

model_id() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"][sys.argv[2]]["model_id"])' "$CONFIG" "$1"; }
get() {  # <role> <hub> [hf download filters]; repeat --include per pattern (hf 2.x)
    local role=$1 hub=$2 id; shift 2
    id=$(model_id "$role")
    echo "== $role: ${id%@*} @ ${id#*@} -> $hub"
    "$HF" download "${id%@*}" --revision "${id#*@}" --cache-dir "$hub" "$@"
}
get assessment "$ASSESSOR_HUB"
get learner "$MODEL_HUB" --include "*.json" --include "*.jinja" --include "*.safetensors"
# Only the HF-format weights (the sbatch pins --config-format hf); skips consolidated.safetensors.
get coach "$MODEL_HUB" --include "*.json" --include "*.jinja" --include "model-*.safetensors"
# Skips original/ and metal/ copies of the weights.
get evaluator "$MODEL_HUB" --include "*.json" --include "*.jinja" --include "model-*.safetensors"
echo "done; set the same ASSESSOR_HUB / MODEL_HUB / SCRATCH_DIR when you sbatch"
