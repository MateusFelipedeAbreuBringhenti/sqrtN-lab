# v0.1 validation

Validated on 2026-10-12 with an NVIDIA GeForce RTX 4060 Laptop GPU,
CUDA 12.4, SM 8.9, and the pinned upstream commit.

## Smoke

- 6 runs: two each at 20, 24, and 28 bits.
- 6/6 completed and recovered secrets verified in memory.
- Actual kangaroos: 8,192 from solver output.
- Operation resolution: 524,288 completed walker-steps.
- No private key or regenerating seed persisted.

The entire low-bit run completes within one GPU batch, confirming that smoke
mode is suitable for correctness but not tail inference.

## Research mini-campaign

- 8 runs: two each at 56, 60, 62, and 64 bits, randomized order.
- 8/8 completed and verified.
- Actual kangaroos: 393,216 from solver output.
- Operation resolution: 25,165,824 completed walker-steps.
- Observed luck-factor range: 0.508× to 3.340×.
- No unredacted private key appeared in results or solver logs.

These validation datasets are deliberately ignored by Git. The committed mode
configuration freezes the first full research campaign at 100 repetitions per
case; operators should choose when to spend the GPU time.

## Clean-environment reproduction

On 2026-10-12, a fresh local clone was initialized with its pinned submodule and
a new Python virtual environment. Installing only `requirements.txt` plus the
test runner produced:

- 6/6 Python tests passed.
- 3/3 smoke runs completed and recovered secrets verified in memory.
- Smoke cases covered 20, 24, and 28 bits in randomized order.

The externally built CUDA solver required its CUDA 12 runtime directory in
`LD_LIBRARY_PATH`; without that loader configuration it could not locate
`libcudart.so.12`. The README now documents this runtime prerequisite explicitly.
