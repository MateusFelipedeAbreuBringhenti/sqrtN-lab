#!/usr/bin/env python3
"""Run synthetic-only secp256k1 Pollard Kangaroo campaigns."""

import argparse
import hashlib
import json
import math
import os
import random
import re
import secrets
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ecdsa import SECP256k1, SigningKey

from canonical_config import config_hash, semantic_config

ROOT = Path(__file__).resolve().parents[1]
MODES = {name: ROOT / "modes" / f"{name}.json" for name in ("smoke", "research", "miracle")}
LAB_RESULT_RE = re.compile(
    r"LAB_RESULT key_index=(?P<key_index>\d+) "
    r"observed_operations=(?P<observed>\d+) "
    r"expected_operations=(?P<expected>\d+) "
    r"operation_resolution=(?P<resolution>\d+) "
    r"kangaroos=(?P<kangaroos>\d+)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def compressed_pubkey(secret: int) -> str:
    point = SigningKey.from_secret_exponent(secret, curve=SECP256k1).verifying_key.pubkey.point
    return ("02" if point.y() % 2 == 0 else "03") + f"{point.x():064x}"


def challenge_hash(bits: int, public_key: str) -> str:
    material = f"sqrtN-lab-v1|0|{(1 << bits) - 1:X}|{public_key.upper()}".encode("ascii")
    return hashlib.sha256(material).hexdigest()


def query_gpu() -> dict:
    fields = [
        "name", "driver_version", "compute_cap", "memory.total",
        "temperature.gpu", "utilization.gpu", "memory.used", "power.draw",
        "clocks.sm", "clocks.mem", "power.limit",
    ]
    command = ["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"]
    try:
        raw = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip().split(", ")
    except (OSError, subprocess.SubprocessError):
        return {field: None for field in fields}

    def number(value: str):
        if value in {"N/A", "[N/A]", "Not Supported"}:
            return None
        try:
            return float(value)
        except ValueError:
            return value

    return {field: number(value) for field, value in zip(fields, raw)}


def monitor(stop: threading.Event, interval: float, samples: list[dict]) -> None:
    while not stop.is_set():
        sample = query_gpu()
        sample["timestamp"] = utc_now()
        samples.append(sample)
        stop.wait(interval)


def wait_for_cooldown(config: dict) -> None:
    policy = config.get("cooldown", {})
    if not policy.get("enabled"):
        return
    threshold = float(policy["start_below_c"])
    while True:
        temperature = query_gpu().get("temperature.gpu")
        if temperature is None or float(temperature) < threshold:
            return
        time.sleep(float(policy.get("poll_seconds", 2)))


def aggregate(samples: list[dict], field: str, operation: str):
    values = [sample[field] for sample in samples if isinstance(sample.get(field), (int, float))]
    if not values:
        return None
    return max(values) if operation == "max" else sum(values) / len(values)


def redact_solver_output(output: str) -> str:
    return re.sub(r"(Priv:\s*0x)[0-9A-Fa-f]+", r"\1[REDACTED_SYNTHETIC_SECRET]", output)


def latest_count_lower_bound(output: str) -> int | None:
    matches = re.findall(r"\[(?:Count|Cnt) 2\^([0-9.]+)\]", output)
    return int(2 ** float(matches[-1])) if matches else None


def solver_revision(binary: Path) -> dict:
    repository = ROOT / "vendor" / "Kangaroo"
    try:
        commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.SubprocessError:
        commit = None
    return {
        "upstream_commit": commit,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "patchset_sha256": hashlib.sha256(
            (ROOT / "patches" / "kangaroo" / "lab-instrumentation.patch").read_bytes()
        ).hexdigest(),
    }


def run_one(index: int, case: dict, config: dict, binary: Path, campaign: Path) -> dict:
    wait_for_cooldown(config)
    bits = int(case["bits"])
    interval_end = (1 << bits) - 1
    secret = secrets.randbelow(interval_end) + 1
    public_key = compressed_pubkey(secret).upper()
    identifier = challenge_hash(bits, public_key)
    run_id = f"{config['mode']}-{index:06d}"
    started_at = utc_now()
    telemetry: list[dict] = []
    stop = threading.Event()

    challenge_text = f"0\n{interval_end:X}\n{public_key}\n"
    with tempfile.NamedTemporaryFile("w", encoding="ascii", prefix="sqrtn-", suffix=".txt") as challenge:
        challenge.write(challenge_text)
        challenge.flush()
        grid = case["grid"]
        command = [
            str(binary), "-gpu", "-gpuId", str(config["gpu_id"]),
            "-g", f"{grid['x']},{grid['y']}", "-d", str(case["dp_bits"]),
            "-t", str(config["cpu_threads"]), challenge.name,
        ]
        worker = threading.Thread(
            target=monitor,
            args=(stop, config["telemetry_interval_ms"] / 1000.0, telemetry),
            daemon=True,
        )
        worker.start()
        before = query_gpu()
        wall_start = time.perf_counter()
        censored = False
        try:
            process = subprocess.run(
                command,
                cwd=binary.parent,
                env=os.environ.copy(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=config["timeout_seconds"],
            )
            output = process.stdout
            return_code = process.returncode
        except subprocess.TimeoutExpired as error:
            censored = True
            output = (error.stdout or "") + (error.stderr or "")
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            return_code = None
        wall_seconds = time.perf_counter() - wall_start
        after = query_gpu()
        stop.set()
        worker.join()

    found = re.findall(r"Priv:\s*0x([0-9A-Fa-f]+)", output)
    verified = bool(found) and int(found[-1], 16) == secret
    machine = list(LAB_RESULT_RE.finditer(output))
    lab = machine[-1].groupdict() if machine else None
    observed = int(lab["observed"]) if lab else None
    expected = int(lab["expected"]) if lab else None
    resolution = int(lab["resolution"]) if lab else None
    kangaroos = int(lab["kangaroos"]) if lab else None
    status = "censored" if censored else ("completed" if verified and return_code == 0 else "failed")

    telemetry_path = campaign / "telemetry" / f"{run_id}.jsonl"
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    telemetry_path.write_text("".join(json.dumps(item) + "\n" for item in telemetry), encoding="utf-8")
    log_path = campaign / "logs" / f"{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(redact_solver_output(output), encoding="utf-8")

    result = {
        "schema_version": 1,
        "run_id": run_id,
        "run_index": index,
        "mode": config["mode"],
        "bits": bits,
        "range_size": 1 << bits,
        "challenge_hash": identifier,
        "target_origin": "locally_generated_synthetic",
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": status,
        "solution_found": verified,
        "verified": verified,
        "return_code": return_code,
        "wall_seconds": wall_seconds,
        "expected_operations": expected,
        "observed_operations": observed,
        "operation_resolution": resolution,
        "observed_until_lower_bound": latest_count_lower_bound(output) if censored else None,
        "actual_kangaroo_count": kangaroos,
        "actual_kangaroo_count_source": "solver_output" if kangaroos is not None else None,
        "c": observed / math.sqrt(1 << bits) if observed else None,
        "luck_factor": expected / observed if expected and observed else None,
        "telemetry": {
            "samples": len(telemetry),
            "gpu_util_avg_pct": aggregate(telemetry, "utilization.gpu", "avg"),
            "gpu_util_peak_pct": aggregate(telemetry, "utilization.gpu", "max"),
            "vram_peak_mib": aggregate(telemetry, "memory.used", "max"),
            "temperature_peak_c": aggregate(telemetry, "temperature.gpu", "max"),
            "power_draw_peak_w": aggregate(telemetry, "power.draw", "max"),
            "before": before,
            "after": after,
            "path": str(telemetry_path.relative_to(campaign)),
        },
        "solver_log": str(log_path.relative_to(campaign)),
    }
    # Explicitly destroy references to the disposable secret before returning.
    secret = 0
    found.clear()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, help="Override repetitions for a bounded local campaign")
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error(f"Solver binary not found: {binary}")
    if args.repetitions is not None and args.repetitions < 1:
        parser.error("--repetitions must be positive")

    config = json.loads(MODES[args.mode].read_text(encoding="utf-8"))
    if config.get("accept_external_targets") is not False:
        parser.error("Safety invariant violated: external targets must be disabled")
    if config.get("target_origin") != "locally_generated_synthetic":
        parser.error("Safety invariant violated: target origin is not synthetic")
    if args.repetitions is not None:
        config["repetitions_per_case"] = args.repetitions

    campaign = args.output.resolve()
    campaign.mkdir(parents=True, exist_ok=False)
    initial_gpu = query_gpu()
    revision = solver_revision(binary)
    manifest = {
        "manifest_schema_version": 1,
        "experiment_id": campaign.name,
        "generated_at": utc_now(),
        "methodology_version": config["methodology_version"],
        "config_hash_algorithm": "sha256",
        "config_hash_canonicalization": "RFC8785-JCS",
        "config_hash_schema_version": 1,
        "config_hash": config_hash(config),
        "semantic_config": semantic_config(config),
        "solver": revision,
        "hardware": {
            "gpu_model": initial_gpu.get("name"),
            "driver_version": initial_gpu.get("driver_version"),
            "compute_capability": initial_gpu.get("compute_cap"),
            "vram_total_mib": initial_gpu.get("memory.total"),
            "power_limit_w": initial_gpu.get("power.limit"),
            "power_limit_source": "nvidia-smi" if initial_gpu.get("power.limit") is not None else "unavailable",
        },
    }
    (campaign / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    schedule = [case for case in config["cases"] for _ in range(config["repetitions_per_case"])]
    if config["randomize_order"]:
        random.SystemRandom().shuffle(schedule)
    results_path = campaign / "runs.jsonl"
    failures = 0
    with results_path.open("a", encoding="utf-8") as results_file:
        for index, case in enumerate(schedule, 1):
            result = run_one(index, case, config, binary, campaign)
            results_file.write(json.dumps(result) + "\n")
            results_file.flush()
            print(json.dumps({key: result[key] for key in ("run_id", "bits", "status", "wall_seconds", "luck_factor")}), flush=True)
            failures += result["status"] == "failed"
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
