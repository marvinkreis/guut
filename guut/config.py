from pathlib import Path

from loguru import logger

default_config_file_location = Path.home() / ".config" / "guut" / "config.py"
cwd_config_file_location = Path(".") / "config.py"


openai_api_key: str = ""
openai_organization: str = ""
quixbugs_path: str = ""
logging_path: str = ""


for path in [default_config_file_location, cwd_config_file_location]:
    if path.is_file():
        logger.info(f"Reading config file: {path}")
        exec(path.read_text())


values = {
    "openai_api_key": openai_api_key,
    "openai_organization": openai_organization,
    "quixbugs_path": quixbugs_path,
    "logging_path": logging_path,
}

valid = True
for name, value in values.items():
    if value is None or value == "":
        logger.warning(f"Missing config value: {name}")
        valid = False

if not valid:
    raise Exception("Missing config values.")
