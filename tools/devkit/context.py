"""One source for project settings, with ignored machine-specific overrides."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from .common import merge, read_json


@dataclass(frozen=True)
class Context:
    root: Path
    config: dict

    @classmethod
    def load(cls, root=None, local=None):
        root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        config = read_json(root / "devtools.json")
        if not isinstance(config, dict):
            raise ValueError('Project configuration must be an object')
        local = Path(local) if local else root / ".devtools.local.json"
        if local.exists():
            override = read_json(local)
            if not isinstance(override, dict):
                raise ValueError('Local configuration must be an object')
            config = merge(config, override)
        if config.get("schema_version") != 1:
            raise ValueError("Unsupported devtools configuration schema")
        if os.environ.get("HBE_GAME_DIR"):
            config["game"] = os.environ["HBE_GAME_DIR"]
        for key in ('mod', 'runs', 'game'):
            if not isinstance(config.get(key), str) or not config[key]:
                raise ValueError('Configure a nonempty path for ' + key)
        workshop = config.get('workshop', {})
        if not isinstance(workshop, dict) or any(type(workshop.get(k)) is not int or workshop[k] <= 0 for k in ('app_id', 'item_id')):
            raise ValueError('Workshop app_id and item_id must be positive integers')
        languages = workshop.get('languages')
        if not isinstance(languages, list) or not languages or any(not isinstance(v, str) or not v.isalpha() for v in languages) or len(set(languages)) != len(languages):
            raise ValueError('Workshop languages must be unique language identifiers')
        return cls(root, config)

    def path(self, key):
        value = self.config.get(key)
        if not value:
            raise ValueError(f"Configure {key} in .devtools.local.json")
        path = Path(value).expanduser()
        return (path if path.is_absolute() else self.root / path).resolve()

    @property
    def mod(self):
        return self.path("mod")

    @property
    def metadata(self):
        return read_json(self.mod / ".metadata/metadata.json")

    @property
    def executable(self):
        return self.path("game") / "binaries/eu5.exe"

    def doctor(self):
        return dict(root=str(self.root), python=sys.executable,
                    version=self.metadata["version"], mod=str(self.mod),
                    game=str(self.executable), game_available=self.executable.is_file(),
                    settings_configured=bool(self.config.get("settings_template")),
                    workshop=self.config["workshop"])
