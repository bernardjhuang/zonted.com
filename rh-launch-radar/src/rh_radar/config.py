from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
CONFIG_PATH = ROOT / "config" / "addresses.yaml"
ENV_CANDIDATES = (
    Path.home() / ".config" / "trading" / "blockscout.env",
    ROOT / ".env",
)


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_api_key() -> str:
    for path in ENV_CANDIDATES:
        load_dotenv_file(path)
    key = os.environ.get("BLOCKSCOUT_PRO_API_KEY", "").strip()
    if not key.startswith("proapi_"):
        raise RuntimeError(
            "BLOCKSCOUT_PRO_API_KEY missing. Put it in ~/.config/trading/blockscout.env "
            "(chmod 600) or export it in the shell."
        )
    return key


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open() as handle:
        return yaml.safe_load(handle)


def ensure_data_dirs() -> None:
    for path in (DATA, RAW, DATA / "features", DATA / "labels", DATA / "scores"):
        path.mkdir(parents=True, exist_ok=True)
