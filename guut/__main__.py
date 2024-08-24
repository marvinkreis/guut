import sys
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.environ["DOTENV_PATH"])

from guut.main import main

if __name__ == "__main__":
    sys.exit(main())
