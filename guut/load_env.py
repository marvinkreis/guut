import os

from dotenv import load_dotenv


def load_env():
    load_dotenv(dotenv_path=os.environ["DOTENV_PATH"])
