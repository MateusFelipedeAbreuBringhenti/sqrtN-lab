#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cuda_root=${CUDA_HOME:?Set CUDA_HOME to the CUDA toolkit directory}
host_cxx=${HOST_CXX:?Set HOST_CXX to a CUDA-compatible g++ executable}
ccap=${CUDA_CCAP:-89}

patch_file="$repo_root/patches/kangaroo/lab-instrumentation.patch"
if git -C "$repo_root/vendor/Kangaroo" apply --check "$patch_file" 2>/dev/null; then
  git -C "$repo_root/vendor/Kangaroo" apply "$patch_file"
elif git -C "$repo_root/vendor/Kangaroo" apply --reverse --check "$patch_file" 2>/dev/null; then
  echo "Instrumentation patch is already applied."
else
  echo "Instrumentation patch does not apply cleanly." >&2
  exit 1
fi

make -C "$repo_root/vendor/Kangaroo" clean
make -C "$repo_root/vendor/Kangaroo" -j"$(nproc)" \
  gpu=1 ccap="$ccap" CUDA="$cuda_root" CXXCUDA="$host_cxx" CXX="$host_cxx" all

echo "Built: $repo_root/vendor/Kangaroo/kangaroo"
