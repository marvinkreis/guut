import os
from dataclasses import asdict, dataclass
from pathlib import Path

from loguru import logger

DEFAULT_CONFIG_FILE_LOCATION = Path.home() / ".config" / "guut" / "config.py"
UNSET_VALUE = "UNSET"


@dataclass
class Config:
    openai_api_key: str = UNSET_VALUE
    openai_organization: str = UNSET_VALUE
    quixbugs_path: str = UNSET_VALUE
    logging_path: str = UNSET_VALUE

    def validate(self, *attributes: str):
        valid = True
        for name, value in asdict(self):
            if value == "":
                logger.warning(f"Missing config value: {name}")
                valid = False
        if not valid:
            raise Exception("Missing config values.")

    def read_config_file(self, code: str, path: str):
        logger.info(f"Reading config file: {path}")
        namespace = {}
        exec(code, None, namespace)
        for name, _ in asdict(self):
            if value := namespace.get(name):
                logger.info(f"Setting {name} from config file: {path}")
                setattr(self, name, value)

    def read_env(self):
        for name, _ in asdict(self):
            if value := os.environ[name.upper()]:
                logger.info(f"Setting {name} from environment.")
                setattr(self, name, value)


config = Config()


for path in [DEFAULT_CONFIG_FILE_LOCATION, Path(".") / "config.py"]:
    if path.is_file():
        config.read_config_file(path.read_text(), path=str(path))
config.read_env()
