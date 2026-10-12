# sqrtN-lab

**Experimental Pollard Kangaroo Runtime Statistics on secp256k1**

> **CONTROLLED LABORATORY — only locally generated synthetic challenges.**
> No Bitcoin Puzzle #140 data, real wallets, third-party keys, or funds.

`sqrtN-lab` measures the runtime distribution, hidden constant, censoring,
and record statistics of Pollard Kangaroo on disposable secp256k1 challenges.
The runner generates every secret internally and exposes no option for an
external public key, address, challenge file, or target.

## Scientific question

How does Pollard Kangaroo convergence behave on synthetic secp256k1 interval
discrete-log challenges, and how do its extremes evolve as the number of
independent trials grows?

## Modes

- `smoke`: 20, 24, and 28-bit correctness checks.
- `research`: repeated 56, 60, 62, and 64-bit trials.
- `miracle`: synthetic 64-bit trials focused on early-convergence records.

The private key exists only in runner memory. Public datasets contain a
challenge hash, not the private key or a seed capable of regenerating it.

## Quick start

Requirements: Python 3.11+, an NVIDIA GPU, a CUDA-built patched Kangaroo
binary, and packages from `requirements.txt`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
make patch-solver
make freeze-manifests

.venv/bin/python scripts/run_experiment.py \
  --mode smoke \
  --binary /absolute/path/to/kangaroo \
  --output results/smoke-v0.1

.venv/bin/python scripts/analyze_results.py \
  results/smoke-v0.1/runs.jsonl \
  --output results/smoke-v0.1/analysis.json
```

The full methodology is in [docs/methodology.md](docs/methodology.md).

To build the patched solver, set `CUDA_HOME`, `HOST_CXX`, and optionally
`CUDA_CCAP` (defaults to 89), then run `make build-solver`. CUDA/glibc compiler
compatibility is distribution-specific and is documented rather than hidden.

## Primary quantities

```text
C = observed_operations / sqrt(N)
luck_factor = expected_operations / observed_operations
```

On a parallel GPU, `observed_operations` is the exact number of completed
walker-steps reported at the batch containing the useful collision. It is
quantized by `operation_resolution`; it is not presented as a fictional
serial ordering inside a parallel batch.

Timeouts remain in the dataset as right-censored observations.

## Scope

This repository is exclusively for controlled cryptographic experiments using
random, disposable private keys owned by the experimenter. Do not modify it to
accept or attack third-party wallets, real funds, or public cryptocurrency
puzzles.

## Licensing

The laboratory code and patches are GPL-3.0. The pinned JeanLucPons/Kangaroo
submodule is independently copyrighted and GPL-3.0 licensed.

## Unofficial objective

```text
If the RNG gods intervene, commit the CSV before celebrating.
```
