#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from canonical_config import canonical_bytes, config_hash, semantic_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    semantic = semantic_config(config)
    manifest = {
        "manifest_schema_version": 1,
        "methodology_version": config["methodology_version"],
        "config_hash_algorithm": "sha256",
        "config_hash_canonicalization": "RFC8785-JCS",
        "config_hash_schema_version": 1,
        "config_hash": config_hash(config),
        "semantic_config": semantic,
        "canonical_config_utf8": canonical_bytes(config).decode("utf-8"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest["config_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
