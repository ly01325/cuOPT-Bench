# 1. Build cuOPT from a pull request

`scripts/build_cuopt_pr.sh` automates everything below. This page explains each step so you can run or debug them by hand.

## 1.1 Check the machine first (read-only commands)

```bash
nvidia-smi                       # note "Driver Version" and the "CUDA Version" in the top-right corner
nvidia-smi -L                    # every GPU you expect must be listed
nproc; free -g | head -2
df -h .                          # the build environment needs roughly 20-30 GB
curl -sI -m 8 https://github.com | head -1
curl -sI -m 8 https://conda.anaconda.org | head -1
```

**Rule: build with a CUDA version no higher than the `CUDA Version` shown by `nvidia-smi`.** If the driver supports CUDA 13.0 and
you build against CUDA 13.4, the binary starts but cannot see any GPU (`cudaGetDeviceCount err=999`).

## 1.2 Get the source and switch to the PR

```bash
git clone https://github.com/NVIDIA/cuopt.git cuopt_src
cd cuopt_src
git fetch origin pull/2338/head:pr2338      # any PR number works
git checkout pr2338
git log --oneline -1                        # note the commit, e.g. 700828b
cat VERSION                                 # a PR is usually based on the development branch, not on the last release
```

A PR branch is normally based on the development branch, so it is **not the same code as the released version**. This matters when
you compare timings against the released wheel (see [Interpreting the results](03-interpreting-results.md)).

## 1.3 Create the build environment

The repository ships conda environment files in `conda/environments/`. They pin a `cuda-version`; replace it with the version
your driver supports.

```bash
mkdir -p mm && curl -sL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C mm bin/micromamba
export MAMBA_ROOT_PREFIX=$PWD/mm_root

ENV_FILE=$(ls cuopt_src/conda/environments/all_cuda-*_arch-x86_64.yaml | sort | tail -1)
sed 's/cuda-version=[0-9.]*/cuda-version=13.0/' "$ENV_FILE" > env_cuda.yaml
grep -n cuda-version env_cuda.yaml          # confirm the change

./mm/bin/micromamba create -y -n cuopt_build -f env_cuda.yaml    # a few minutes, large download
```

## 1.4 Build only what the command-line benchmark needs

```bash
eval "$(./mm/bin/micromamba shell hook -s bash)"
micromamba activate cuopt_build
cd cuopt_src
./build.sh libcuopt --skip-tests-build --skip-routing-build --skip-grpc-build --skip-c-python-adapters
```

About 10 minutes on a 224-thread machine. Success ends with `Linking CXX executable cuopt_cli`. The binary is
`cuopt_src/cpp/build/cuopt_cli`.

At run time it needs the environment's libraries:

```bash
export LD_LIBRARY_PATH=<MAMBA_ROOT_PREFIX>/envs/cuopt_build/lib
```

## 1.5 Smoke test

```bash
python scripts/convert_lp_to_mps.py examples/tiny_schedule.lp tiny.mps
CUDA_VISIBLE_DEVICES=0 cuopt_src/cpp/build/cuopt_cli tiny.mps --time-limit 10 2>&1 | head -15
```

| Good | Bad |
|---|---|
| `CUDA 13.0, device: NVIDIA ... (ID 0), VRAM: ...` | `cuOpt selected CPU memory backend: no usable CUDA device (... err=999 ...)` |

Do not continue with a failing smoke test. See [Troubleshooting](04-troubleshooting.md).

## 1.6 The released version as a baseline (optional)

To show that a difference comes from the PR and not from the environment, also run the released `cuopt_cli`. Install the matching
`cuopt-cu13` wheel into a separate virtual environment by following NVIDIA's installation documentation, and pass its
`cuopt_cli` to `run_compare.sh` as `ORIG_CLI`.
