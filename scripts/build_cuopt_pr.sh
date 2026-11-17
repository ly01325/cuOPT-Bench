#!/bin/bash
# Build cuopt_cli from a cuOPT pull-request branch (or any git ref) inside a micromamba environment.
#
# usage:  PR=2338 bash scripts/build_cuopt_pr.sh [workdir]
#         REF=main bash scripts/build_cuopt_pr.sh [workdir]          # build a branch/tag instead of a PR
# options (environment variables):
#   PR            pull request number to build (default: unset)
#   REF           git ref to build when PR is unset (default: main)
#   CUDA_VERSION  conda "cuda-version" to build with, e.g. 13.0. Default: the CUDA version your driver supports,
#                 read from nvidia-smi. Never pick a version higher than the driver supports.
#   ENV_NAME      conda environment name (default: cuopt_build)
#
# Result: <workdir>/cuopt_src/cpp/build/cuopt_cli and the library dir printed at the end (use it as LD_LIBRARY_PATH).
# Tested on x86_64 Linux. The commands were run step by step on such a machine; this wrapper itself
# was written afterwards from those steps, so run it once on a spare machine before relying on it.
set -euo pipefail

WORK=${1:-$PWD/work}
PR=${PR:-}
REF=${REF:-main}
ENV_NAME=${ENV_NAME:-cuopt_build}

case "$(uname -m)" in
  x86_64)  MM_PLATFORM=linux-64 ;;
  aarch64) MM_PLATFORM=linux-aarch64 ;;
  *) echo "unsupported architecture: $(uname -m)"; exit 1 ;;
esac

# 1. pick the CUDA version from the driver unless given
if [ -z "${CUDA_VERSION:-}" ]; then
  CUDA_VERSION=$(nvidia-smi | sed -n 's/.*CUDA Version: \([0-9]*\.[0-9]*\).*/\1/p' | head -1)
  [ -n "$CUDA_VERSION" ] || { echo "cannot read the CUDA version from nvidia-smi; set CUDA_VERSION=13.0"; exit 1; }
fi
echo "[1/5] building with cuda-version=$CUDA_VERSION"

mkdir -p "$WORK"; cd "$WORK"

# 2. source
if [ ! -d cuopt_src ]; then git clone https://github.com/NVIDIA/cuopt.git cuopt_src; fi
cd cuopt_src
if [ -n "$PR" ]; then
  echo "[2/5] fetching PR $PR"
  git fetch origin "pull/$PR/head:pr$PR"
  git checkout "pr$PR"
else
  echo "[2/5] checking out $REF"
  git fetch origin "$REF" || true
  git checkout "$REF"
fi
git log --oneline -1
echo "VERSION: $(cat VERSION 2>/dev/null || echo unknown)"
cd "$WORK"

# 3. micromamba
export MAMBA_ROOT_PREFIX=$WORK/mm_root
if [ ! -x "$WORK/micromamba" ]; then
  echo "[3/5] installing micromamba"
  mkdir -p "$WORK/mm_tmp"
  curl -sL "https://micro.mamba.pm/api/micromamba/$MM_PLATFORM/latest" | tar -xj -C "$WORK/mm_tmp" bin/micromamba
  mv "$WORK/mm_tmp/bin/micromamba" "$WORK/micromamba"
fi

# 4. environment: take the repo's environment file and swap in the CUDA version that matches the driver
ENV_FILE=$(ls cuopt_src/conda/environments/all_cuda-*_arch-"$(uname -m)".yaml | sort | tail -1)
echo "[4/5] creating conda env $ENV_NAME from $ENV_FILE (cuda-version=$CUDA_VERSION)"
sed "s/cuda-version=[0-9.]*/cuda-version=$CUDA_VERSION/" "$ENV_FILE" > "$WORK/env_cuda.yaml"
grep -n "cuda-version" "$WORK/env_cuda.yaml"
if ! "$WORK/micromamba" env list | grep -q "$ENV_NAME"; then
  "$WORK/micromamba" create -y -n "$ENV_NAME" -f "$WORK/env_cuda.yaml"
fi

# 5. build only what the command-line benchmark needs
echo "[5/5] building libcuopt and cuopt_cli (about 10 minutes on a 224-thread machine)"
eval "$("$WORK/micromamba" shell hook -s bash)"
micromamba activate "$ENV_NAME"
cd "$WORK/cuopt_src"
./build.sh libcuopt --skip-tests-build --skip-routing-build --skip-grpc-build --skip-c-python-adapters

echo
echo "done."
echo "  cuopt_cli : $WORK/cuopt_src/cpp/build/cuopt_cli"
echo "  libraries : $MAMBA_ROOT_PREFIX/envs/$ENV_NAME/lib   (export LD_LIBRARY_PATH=this before running)"
