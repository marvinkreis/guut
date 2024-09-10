# guut: Generate understandable unit tests

## Setup

- Create a venv (optional): `python -m venv .venv; source .venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Copy `example.config.py` to either `$HOME/.config/guut/config.py` or `./config.py` and fill in the values.
	- `openai_api_key`, `openai_organization`: your openai credentials
	-  `quixbugs_path`: points to the [quixbugs github repo](https://github.com/jkoppel/QuixBugs)
	- `logging_path`: points to a directory, where conversation logs are stored
	- `python_interpreter`: points to the python interpreter to be used for executing code

## Usage

- Use `python -m guut` to run. We'll abbreviate this to just `guut` here.
- List quixbugs tasks: `guut list quixbugs`
- Run a quixbugs task: `guut run quixbugs <task_name>`
- Continue a conversation: `guut run --continue '/path/to/conversation.json' <task_type> <task_name>`
- Replay LLM responses from a conversation: `guut run --replay '/path/to/conversation.json' <task_type> <task_name>`
- Replay LLM responses from a yaml list of strings: `guut run --replay '/path/to/messages.yaml' <task_type> <task_name>`
- Other options:
	- `--outdir`: set the directory that results are written to
	- `-y`: perform LLM completions without asking
	- `--nologs`: disable logging of conversations
	- `--silent`: disable printing of messages
	- `--baseline`: run the baseline implementation
