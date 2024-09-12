import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from loguru import logger

DEFAULT_CONFIG_FILE_LOCATION = Path.home() / ".config" / "guut" / "config.py"
UNSET: Any = object()


@dataclass
class Config:
    _output_path: str = UNSET
    _logging_path: str = UNSET
    _openai_api_key: str = UNSET
    _openai_organization: str = UNSET
    _quixbugs_path: str = UNSET
    _python_interpreter: str = UNSET

    @property
    def output_path(self) -> Path:
        return self._validate_path("output_path", self._output_path)

    @property
    def logging_path(self) -> Path:
        return self._validate_path("loggin_path", self._logging_path)

    @property
    def openai_api_key(self) -> str:
        return self._validate("openai_api_key", self._openai_api_key)

    @property
    def openai_organization(self) -> str:
        return self._validate("openai_organization", self._openai_organization)

    @property
    def quixbugs_path(self) -> Path:
        return self._validate_path("quixbugs_path", self._quixbugs_path)

    @property
    def python_interpreter(self) -> Path:
        return self._validate_path("python_interpreter", self._python_interpreter)

    def _validate(self, key: str, value: Any) -> Any:
        if value is UNSET:
            logger.warning(f"Missing config value: {key}")
            raise Exception(f"Missing config value: {key}")
        return value

    def _validate_path(self, key: str, value: str) -> Path:
        self._validate(key, value)
        path = Path(value)
        if not path.exists():
            raise Exception(f"Path for '{key}' does not exist: '{value}'.")
        return path

    def read_config_file(self, code: str, path: str):
        logger.debug(f'Reading config file: "{path}"')
        namespace = {}
        exec(code, None, namespace)
        for name, _ in asdict(self).items():
            if value := namespace.get(name[1:]):
                logger.debug(f'Setting "{name[1:]}" from config file: "{path}"')
                setattr(self, name, value)

    def read_env(self):
        for name, _ in asdict(self).items():
            if value := os.environ.get(name[1:].upper()):
                logger.debug(f'Setting "{name[1:]}" from env variable.')
                setattr(self, name, value)


config = Config()

for path in [DEFAULT_CONFIG_FILE_LOCATION, Path(".") / "config.py"]:
    if path.is_file():
        config.read_config_file(path.read_text(), path=str(path))
config.read_env()
