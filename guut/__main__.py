import sys

from guut.load_env import load_env

load_env()

from guut.main import main

if __name__ == "__main__":
    sys.exit(main())
