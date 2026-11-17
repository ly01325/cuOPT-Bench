#!/bin/bash
# cuOPT (PR build, optionally the released wheel) vs HiGHS vs SCIP on one MPS model, run strictly one after another.
#
# usage:
#   MODEL=model.mps PR_CLI=/path/to/cuopt_cli PR_LIB=/path/to/conda_env/lib PY=/path/to/python \
#   [ORIG_CLI=/path/to/released/cuopt_cli] bash scripts/run_compare.sh [outdir]
#
# environment variables:
#   MODEL       MPS model (required)
#   PR_CLI      cuopt_cli built from the PR branch (required)
#   PR_LIB      directory for LD_LIBRARY_PATH of that build, i.e. <conda env>/lib (required)
#   PY          python that has ortools, highspy and numpy (required)
#   ORIG_CLI    cuopt_cli from the released wheel, used as the baseline (optional)
#   TL          cuOPT time limit in seconds (default 600)
#   TL_OTHER    HiGHS / SCIP time limit in seconds (default 1800)
#   SCIP_PARAM  SCIP parameter, exactly one "key = value" (default "numerics/feastol = 1e-5"; set "" for SCIP defaults)
#   GPU         GPU index for cuOPT (default 0)
#
# Run it on an otherwise idle machine; the solvers all use every core, so overlapping runs distort the times.
# Every log ends with a line "WALL <seconds>" = wall-clock time of the whole process.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
MODEL=${MODEL:?set MODEL=path/to/model.mps}
PR_CLI=${PR_CLI:?set PR_CLI=.../cpp/build/cuopt_cli}
PR_LIB=${PR_LIB:?set PR_LIB=<conda env>/lib}
PY=${PY:?set PY=python with ortools, highspy, numpy}
ORIG_CLI=${ORIG_CLI:-}
TL=${TL:-600}
TL_OTHER=${TL_OTHER:-1800}
SCIP_PARAM=${SCIP_PARAM-numerics/feastol = 1e-5}
GPU=${GPU:-0}
OUT=${1:-out_cmp}

rm -rf "$OUT"; mkdir -p "$OUT"
export CUDA_VISIBLE_DEVICES=$GPU

timed() {  # run a command, then print its wall time as the last line
  local s e
  s=$(date +%s.%N); "$@"; e=$(date +%s.%N)
  awk -v s="$s" -v e="$e" 'BEGIN{printf "WALL %.1f\n", e - s}'
}

for i in 1 2; do   # cuOPT is randomised; run the PR build twice and check that the runs agree
  { LD_LIBRARY_PATH=$PR_LIB timed "$PR_CLI" "$MODEL" --time-limit "$TL" --solution-file "$OUT/cuopt_pr_$i.sol"; } > "$OUT/cuopt_pr_$i.log" 2>&1
done
if [ -n "$ORIG_CLI" ]; then
  { timed "$ORIG_CLI" "$MODEL" --time-limit "$TL" --solution-file "$OUT/cuopt_orig.sol"; } > "$OUT/cuopt_orig.log" 2>&1
fi
{ timed "$PY" -u "$HERE/run_highs_native.py" "$MODEL" "$TL_OTHER" "$OUT"; } > "$OUT/highs.log" 2>&1
{ timed "$PY" -u "$HERE/run_ortools.py" scip "$MODEL" "$TL_OTHER" "$SCIP_PARAM" "$OUT/scip.sol"; } > "$OUT/scip.log" 2>&1

echo ALLDONE > "$OUT/DONE"
echo "finished. next:  $PY $HERE/summarize_logs.py $OUT"
