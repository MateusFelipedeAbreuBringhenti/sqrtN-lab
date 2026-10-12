# Methodology v0.1

## Scope and invariant

Every challenge is generated locally immediately before its run. The runner
has no input for an address, public key, arbitrary interval, challenge file,
or external target. The generated secret is used to verify the recovered
answer and is then discarded.

## Experimental unit

One run consists of:

1. Generate a uniformly random nonzero scalar in `[1, 2^bits - 1]`.
2. Derive its compressed secp256k1 public key.
3. Write a temporary solver input with interval `[0, 2^bits - 1]`.
4. Run the pinned, patched solver with the frozen configuration.
5. Verify the recovered scalar in memory.
6. Persist only the challenge hash, measurements, and verification outcome.
7. Delete the temporary input.

## Primary measurement

The primary work variable is completed walker-steps at the GPU batch that
contains the useful collision. The patched solver emits this value after all
workers join. Because GPU execution is parallel and batched, there is no
unique serial ordering within the final batch. Results therefore include an
`operation_resolution` equal to one completed batch.

Wall time is an engineering measurement, not a substitute for operation
count. It includes context and herd initialization unless explicitly separated.

## Derived quantities

For interval width `N`:

```text
C = observed_operations / sqrt(N)
luck_factor = expected_operations / observed_operations
```

An observation with `luck_factor > 1` converged earlier than the solver's
expectation. Records are not interpreted without the number of trials already
performed.

## Censoring

A timeout produces a retained record with `status = "censored"`,
`solution_found = false`, and the last periodic operation count as a lower
bound when available. Censored runs are excluded from naive means and must be
handled with survival-aware methods in inferential work.

## Tail estimates

For completed runs:

```text
in_sample_tail = count(luck_factor >= current) / completed_runs
```

Record-discovery samples must not be used as independent confirmation of their
own rarity. A later, frozen holdout campaign is required for `holdout_tail`.

## Thermal and ordering controls

Case order is randomized per campaign. Research modes wait for the GPU to fall
below the configured starting temperature. Per-run telemetry records GPU
utilization, VRAM, temperature, power draw, and clocks when the driver exposes
them. Missing driver fields remain null; values are never invented.

## Manifest and hashing

The immutable manifest describes what should remain fixed. Run results describe
what happened. Telemetry is stored separately. Derived statistics can always be
regenerated.

The semantic configuration object excludes timestamps, experiment identifiers,
telemetry, and derived values. It is serialized with RFC 8785 JSON Canonicalization
Scheme and hashed with SHA-256. The canonicalization and schema versions are
recorded alongside the hash.

## Reproducibility limitation

The pinned upstream solver does not expose deterministic control of its internal
random seed. v0.1 records this honestly as `solver_seed_control =
"unavailable_upstream"`. Challenge secrets and their seeds are intentionally not
published.
