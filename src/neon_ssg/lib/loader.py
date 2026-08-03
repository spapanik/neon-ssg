from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dj_settings import ConfigParser

from neon_ssg.lib.exceptions import UnreadableConfigError

CONFIG_FILENAME: Final = "neon-ssg.yaml"
ENV_NAMESPACE: Final = "NEON_SSG"
DIR_NAMESPACE: Final = "neon-ssg"


@dataclass(frozen=True, slots=True)
class ConfigSource:
    parser: ConfigParser
    stem: Path
    resolution_root: Path


def _stem(config_file: Path | None) -> Path:
    if config_file is None:
        return Path.cwd() / CONFIG_FILENAME

    stem = config_file.resolve()
    if not stem.is_file():
        msg = f"config file not found: {config_file}"
        raise UnreadableConfigError(msg)

    if not os.access(stem, os.R_OK):
        msg = f"config file is not readable: {config_file}"
        raise UnreadableConfigError(msg)

    return stem


def _parser(stem: Path) -> ConfigParser:
    try:
        parser = ConfigParser(stem, dir_namespace=DIR_NAMESPACE)
        _ = parser.data
    except Exception as exc:
        msg = f"cannot read the configuration at '{stem}': {exc}"
        raise UnreadableConfigError(msg) from exc

    return parser


def discover(config_file: Path | None = None) -> ConfigSource:
    stem = _stem(config_file)
    return ConfigSource(parser=_parser(stem), stem=stem, resolution_root=stem.parent)
