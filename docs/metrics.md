# Metrics

## Manifest

- Solver and patch commits
- Canonical semantic configuration and SHA-256 hash
- GPU, driver, CUDA, grid, DP bits, timeout, and thermal policy
- `power_limit_w`, nullable when unavailable
- Actual kangaroo count and its evidence source

## Run result

- Run index, case, status, challenge hash, and verification
- Expected and observed operations
- Operation resolution and censoring lower bound
- Wall and solver compute time when available
- Throughput and derived `C`/`luck_factor`

## Telemetry

- GPU utilization
- VRAM used
- Temperature
- Power draw
- SM and memory clocks

## Derived campaign statistics

- P10, P50, mean, P90, P95, P99, minimum, maximum, standard deviation
- In-sample empirical tail probability
- Best and worst luck so far, with discovery run index
- Censored count reported separately
