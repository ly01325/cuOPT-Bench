# cuOPT vs OR-Tools: build cuOPT from a PR and benchmark it

Scripts and a step-by-step guide to

1. **build `cuopt_cli` from a cuOPT pull-request branch** (or any git ref) on a Linux GPU machine,
2. **run the same MIP/LP model** with cuOPT, SCIP and HiGHS (the last two through OR-Tools or natively),
3. **check every returned solution independently** against the original model, and
4. **summarise the timings and solution quality** in one table.

It grew out of a concrete case: on a large scheduling MIP, presolve removed every integer variable, cuOPT 26.10 solved the
remaining LP correctly but returned no solution, and [NVIDIA/cuopt PR 2338](https://github.com/NVIDIA/cuopt/pull/2338)
("Set correct MIP tolerances for reduced-to-LP problems") fixed it. The workflow is general, so you can use it for any
PR or model. The business model from that case is **not** part of this repository; see
[docs/reference-results.md](docs/reference-results.md) for the numbers.

> Results depend on the model, the machine and the cuOPT version. Treat them as one data point, not a general ranking.

## What is in here

| Path | What it does |
|---|---|
| `scripts/build_cuopt_pr.sh` | clones cuOPT, checks out a PR (or ref), creates a micromamba environment with the right CUDA version, builds `cuopt_cli` |
| `scripts/convert_lp_to_mps.py` | converts `.lp` to `.mps` (cuopt_cli reads MPS) |
| `scripts/run_ortools.py` | solves an MPS with an OR-Tools solver (SCIP, HiGHS, ...) and optionally dumps the solution |
| `scripts/run_highs_native.py` | solves an MPS with HiGHS through `highspy`, without OR-Tools in between |
| `scripts/run_compare.sh` | runs cuOPT (PR build, optional released baseline), HiGHS and SCIP one after another and writes logs |
| `scripts/summarize_logs.py` | turns those logs into a Markdown table |
| `scripts/verify_solution.py` | recomputes objective, row/bound violation and integrality of a solution on the original model |
| `examples/tiny_schedule.lp` | a 27-variable toy model for a smoke test (not a benchmark) |
| `docs/` | build guide, benchmark guide, how to read the results, troubleshooting, reference numbers |
| `docs/zh-CN/handbook.md` | 中文操作手册 |

## Requirements

- Linux (x86_64 tested), an NVIDIA GPU, and a driver new enough for the CUDA version you build with.
  **The build must use a CUDA version no higher than the one `nvidia-smi` reports**, otherwise the binary fails at start-up
  with `cudaGetDeviceCount err=999`.
- Network access to GitHub and conda-forge / RAPIDS channels. About 30 GB of free disk for the build environment.
- Python 3.9+ with `ortools`, `highspy`, `numpy` for the benchmark scripts:
  `pip install ortools highspy numpy`
- The shell scripts use GNU `date` (`%N`), so run them on Linux, not macOS.

## Quick start

```bash
git clone <this repo> && cd cuopt-ortools-benchmark

# 1. build cuopt_cli from PR 2338 (about 10 minutes on a large machine)
PR=2338 bash scripts/build_cuopt_pr.sh ~/cuopt_work
#    -> prints the cuopt_cli path and the library directory (needed as LD_LIBRARY_PATH)

# 2. smoke test the build on the toy model
python scripts/convert_lp_to_mps.py examples/tiny_schedule.lp tiny.mps
LD_LIBRARY_PATH=~/cuopt_work/mm_root/envs/cuopt_build/lib \
  ~/cuopt_work/cuopt_src/cpp/build/cuopt_cli tiny.mps --time-limit 10
#    the log must contain a line like  "CUDA 13.0, device: ..."  (not "no usable CUDA device")

# 3. compare on your own model (an idle machine, one solver at a time)
python scripts/convert_lp_to_mps.py my_model.lp my_model.mps
MODEL=my_model.mps \
PR_CLI=~/cuopt_work/cuopt_src/cpp/build/cuopt_cli \
PR_LIB=~/cuopt_work/mm_root/envs/cuopt_build/lib \
PY=$(which python) \
bash scripts/run_compare.sh out_cmp
python scripts/summarize_logs.py out_cmp

# 4. check each solution you intend to trust
python scripts/verify_solution.py my_model.mps out_cmp/cuopt_pr_1.sol
python scripts/verify_solution.py my_model.mps out_cmp/scip.sol
```

Read [docs/03-interpreting-results.md](docs/03-interpreting-results.md) before quoting any number. In particular, a solver
saying "optimal" is not evidence that the point is feasible, and "success" means different things for different solvers.

## Documentation

1. [Build cuOPT from a PR](docs/01-build-cuopt.md)
2. [Run the benchmark](docs/02-run-benchmark.md)
3. [Interpreting the results](docs/03-interpreting-results.md)
4. [Troubleshooting](docs/04-troubleshooting.md)
5. [Reference results from the original case](docs/reference-results.md)

## Status of the scripts

| Script | Tested |
|---|---|
| `convert_lp_to_mps.py`, `run_ortools.py`, `run_highs_native.py`, `verify_solution.py` | run on the toy model and, in earlier versions, on the large model |
| `summarize_logs.py` | run against the logs of the original case; its output matches the numbers in the reference table |
| `run_compare.sh` | its control flow was tested with a stub `cuopt_cli`; the earlier, hard-coded version ran on the real machine |
| `build_cuopt_pr.sh` | the individual commands were run on the real machine; the wrapper script was written afterwards and has **not** been run end to end |

## License

Apache-2.0, see [LICENSE](LICENSE). cuOPT, OR-Tools, SCIP and HiGHS keep their own licenses.
