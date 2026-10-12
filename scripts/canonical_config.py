#!/usr/bin/env python3
"""RFC 8785 canonical configuration hashing."""

import hashlib
from typing import Any

import rfc8785


NON_SEMANTIC_FIELDS = {
    "experiment_id",
    "generated_at",
    "started_at",
    "finished_at",
    "telemetry",
    "derived_statistics",
    "config_hash",
    "config_hash_algorithm",
    "config_hash_canonicalization",
    "config_hash_schema_version",
}


def semantic_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: semantic_config(item)
            for key, item in value.items()
            if key not in NON_SEMANTIC_FIELDS
        }
    if isinstance(value, list):
        return [semantic_config(item) for item in value]
    return value


def canonical_bytes(config: dict) -> bytes:
    return rfc8785.dumps(semantic_config(config))


def config_hash(config: dict) -> str:
    return hashlib.sha256(canonical_bytes(config)).hexdigest()
