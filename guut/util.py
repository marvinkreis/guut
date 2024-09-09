from pathlib import Path
from subprocess import Popen

from loguru import logger


def ensure_python_coverage_module_is_installed(python_interpreter: Path):
    check_command = [str(python_interpreter), "-m", "coverage"]
    check_process = Popen(check_command)
    check_process.wait()

    if check_process.returncode != 0:
        logger.info(f"Coverage module is not installed. Installing 'coverage' for '{python_interpreter}'...")
        install_command = [str(python_interpreter), "-m", "pip", "install", "coverage"]
        install_process = Popen(install_command)
        install_process.wait()

        if install_process.returncode != 0:
            logger.error("Couldn't install coverage module.")
            raise Exception("Couldn't install coverage module.")
