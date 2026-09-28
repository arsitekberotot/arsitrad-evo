"""Rebuild and validate all V4.1 campaigns and publication layers."""
from __future__ import annotations

import argparse

from arsitrad_evo.campaign_v41 import build_campaign, default_config
from arsitrad_evo.validate_v41 import validate_campaign


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="campaign_v41_verified")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = default_config(smoke=args.smoke)
    manifest = build_campaign(args.out, config)
    gate = validate_campaign(args.out, replay=True)
    if not gate["passed"]:
        raise SystemExit(f"V4.1 publication failed: {gate['errors']}")
    print(f"[publication] {manifest['identity']['campaign_id']} -> {args.out}")


if __name__ == "__main__":
    main()
