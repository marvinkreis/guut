import os

from dotenv import load_dotenv


def load_env():
    if path := os.environ["DOTENV_PATH"]:
        load_dotenv(dotenv_path=path)
    else:
        load_dotenv()
