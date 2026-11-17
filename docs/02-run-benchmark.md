# 2. Run the benchmark

## 2.1 Prepare the Python environment and the model

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install ortools highspy numpy
```

cuOPT's command line reads MPS. Convert an LP file first:

```bash
python scripts/convert_lp_to_mps.py my_model.lp my_model.mps
```

Use the same MPS file for every solver. For a public benchmark set, MIPLIB 2017 instances (https://miplib.zib.de) are available as
`.mps.gz`; unzip them first.

## 2.2 Rules for a fair measurement

- **One solver at a time.** Every solver uses all cores; overlapping runs distort the times. `run_compare.sh` is sequential for this reason.
- **Idle machine.** Check `uptime` and `nvidia-smi` for other jobs before you start.
- **Same model file and the same time limit** for the solvers you compare.
- **Repeat the cuOPT runs** (the script runs the PR build twice). cuOPT is randomised; if two runs disagree a lot, run more.
- **Record the environment**: CPU model and thread count, GPU model, driver, CUDA version, cuOPT commit, OR-Tools version.

## 2.3 Run everything

```bash
MODEL=my_model.mps \
PR_CLI=<workdir>/cuopt_src/cpp/build/cuopt_cli \
PR_LIB=<workdir>/mm_root/envs/cuopt_build/lib \
PY=$(which python) \
ORIG_CLI=/path/to/released/cuopt_cli \
bash scripts/run_compare.sh out_cmp
```

For a long run use `nohup ... &` and wait for `out_cmp/DONE`.

| Log | Command behind it |
|---|---|
| `cuopt_pr_1.log`, `cuopt_pr_2.log` | PR build of `cuopt_cli`, `--time-limit $TL` (default 600 s), one GPU |
| `cuopt_orig.log` | released `cuopt_cli` (only if `ORIG_CLI` is set) |
| `highs.log` | `run_highs_native.py`: HiGHS through `highspy` |
| `scip.log` | `run_ortools.py scip ...` with `numerics/feastol = 1e-5` (change with `SCIP_PARAM`) |

Each log ends with `WALL <seconds>`, the wall time of the whole process (reading, presolve, solve, writing the solution).

Environment variables: `TL` (cuOPT limit), `TL_OTHER` (HiGHS/SCIP limit, default 1800 s), `SCIP_PARAM`, `GPU`.

### Two details that cost time if you do not know them

1. **SCIP takes exactly one `key = value` string** through OR-Tools. `"numerics/feastol = 1e-5 limits/gap = 0.01"` is rejected with
   `INVALID_SOLVER_PARAMETERS`. Run SCIP twice, or use a settings file, if you need several parameters.
2. **Do not mix HiGHS-through-OR-Tools with native HiGHS in one table.** OR-Tools re-checks HiGHS's solution and may change the
   status. In the original case the OR-Tools path took far longer and reported failure while the native run finished quickly.
   Pick one path and say which.

## 2.4 Summarise

```bash
python scripts/summarize_logs.py out_cmp
```

prints a Markdown table of total time, presolve time, LP/solve time and the status each solver printed.

## 2.5 Verify every solution you want to quote

```bash
python scripts/verify_solution.py my_model.mps out_cmp/cuopt_pr_1.sol
python scripts/verify_solution.py my_model.mps out_cmp/scip.sol
```

It recomputes the objective, the largest row and bound violation, the number of rows violated by more than 1e-6, and the largest
distance of an integer variable from an integer, on the original model. The file layout is "name value" lines; header lines starting
with `#` (as in cuopt_cli solution files) are ignored.

The native HiGHS script writes HiGHS's own solution format (`highs_native.sol`), which `verify_solution.py` does not read. HiGHS
prints its own violation summary in the log.

## 2.6 Other cuOPT options worth knowing

| Option | Use |
|---|---|
| `--time-limit S` | limit in seconds |
| `--solution-file F` | write the solution |
| `--first-primal-feasible true`, `--mip-heuristics-only true` | stop at the first feasible point / only heuristics |
| `--mip-absolute-tolerance`, `--mip-relative-tolerance`, `--mip-integrality-tolerance`, `--absolute-primal-tolerance`, `--relative-primal-tolerance` | tolerances |
| `--presolve N`, `--mip-probing true/false` | presolve control |
| `--params-file F` | `key = value` lines for advanced parameters |
| `--num-cpu-threads N` | CPU thread budget |

Check `cuopt_cli --help` for the options of your build. In the original case none of the tolerance options affected the reduced-LP path
before the PR; the PR made that path use the MIP tolerances.
