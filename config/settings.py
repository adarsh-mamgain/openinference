from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
APP_DIR = ROOT / "app"


@dataclass(frozen=True)
class ConfigPaths:
    litellm_config: Path = CONFIG_DIR / "litellm_config.yaml"
    providers: Path = CONFIG_DIR / "providers.json"


PATHS = ConfigPaths()

