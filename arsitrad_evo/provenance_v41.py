"""Content identities for V4.1 code, configuration, site and module data."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .program_v41 import catalogue


ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode("utf-8")).hexdigest()


def code_sha() -> str:
    """Hash source contents, including uncommitted work, not only Git HEAD."""
    files = sorted((ROOT / "arsitrad_evo").glob("*.py"))
    files += [ROOT / "run_campaign_v41.py"]
    digest = hashlib.sha256()
    for path in files:
        if not path.exists():
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def site_data_sha(site_geojson: Path = ROOT / "data/site.geojson",
                  site_yaml: Path = ROOT / "data/site.yaml") -> str:
    digest = hashlib.sha256()
    for path in (site_geojson, site_yaml):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def module_library_sha() -> str:
    return sha256_json(catalogue())


@dataclass(frozen=True)
class CampaignIdentity:
    code_sha: str
    config_hash: str
    site_data_hash: str
    module_library_hash: str
    campaign_id: str

    def asdict(self) -> dict:
        return asdict(self)


def make_identity(config: dict) -> CampaignIdentity:
    code = code_sha()
    cfg = sha256_json(config)
    site = site_data_sha()
    modules = module_library_sha()
    campaign = "v41-" + sha256_json({"code": code, "config": cfg,
                                     "site": site, "modules": modules})[:16]
    return CampaignIdentity(code, cfg, site, modules, campaign)


def assert_current_identity(identity: dict, config: dict) -> None:
    current = make_identity(config).asdict()
    if identity != current:
        changed = [key for key in current if current[key] != identity.get(key)]
        raise ValueError(f"Stale V4.1 artifact identity: {changed}")
