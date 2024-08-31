import json
import pickle
from pathlib import Path
from typing import Tuple

import click
import yaml
from loguru import logger
from openai import OpenAI

from guut.formatting import format_problem
from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import default_prompts
from guut.quixbugs import QuixbugsProblem

problem_types = {"quixbugs": QuixbugsProblem}


@click.group()
def main():
    pass


@main.command(
    "list",
    short_help="Lists task types. Lists tasks. Shows tasks.",
    help="Use <no args> to list task types. Use <type> to list tasks. Use <type:name> to show a task.",
)
@click.argument("task_id", nargs=1, type=str, required=False)
def _list(task_id: str | None):
    if not task_id:
        list_types()
        return

    type, problem_name = parse_problem_id(task_id)
    if not problem_name:
        list_tasks(type)
        return

    show_task(type, problem_name)


def list_types():
    print('Showing available task types. Use "show <type>" to list tasks.\n')
    for type in problem_types.keys():
        print(f"- {type}")


def list_tasks(type: str):
    ProblemType = problem_types.get(type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{type}".')

    print(f'Showing available tasks for {type}. Use "show <type:name>" to show a task.\n')
    problems = ProblemType.list_problems()
    if problems:
        for desc in problems:
            if " " in desc.name:
                print(f'- "{type}:{desc.name}"')
            else:
                print(f"- {type}:{desc.name}")


def show_task(type: str, problem_name: str):
    ProblemType = problem_types.get(type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{type}".')
    if not problem_name:
        raise Exception()

    if " " in problem_name:
        print(f'Showing task "{type}:{problem_name}".\n')
    else:
        print(f"Showing task {type}:{problem_name}.\n")

    problem = ProblemType(problem_name)
    print(format_problem(problem))


@main.command()
@click.argument("task_id", nargs=1, type=str, required=True)
@click.option(
    "--replay",
    nargs=1,
    type=click.Path(exists=True),
    required=False,
    help="Replay LLM responses instead of requesting completions. Path can be a logged .pickle or .json conversation file or a .yaml file containing a list of strings. Iplies -y.",
)
@click.option(
    "--continue",
    "resume",
    nargs=1,
    type=click.Path(exists=True),
    required=False,
    help="Continue a conversation from a logged .pickle or .json conversation file.",
)
@click.option(
    "--index",
    "-n",
    nargs=1,
    type=int,
    required=False,
    help="Use with --continue. Selects the number of messages to pick from the conversation (including all messages). Use negative numbers to exclude messages starting from the end.",
)
@click.option(
    "-y",
    "--yes",
    "unsafe",
    is_flag=True,
    default=False,
    help="Request completions without confirmation. Implies no -s.",
)
@click.option("--silent", "-s", is_flag=True, default=False, help="Don't print the conversation during computation.")
@click.option("--nologs", "-n", is_flag=True, default=False, help="Disable logging.")
def run(
    task_id: str,
    replay: str | None,
    resume: str | None,
    index: int | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
):
    if replay and resume:
        raise Exception("Cannot use --replay and --continue together.")

    type, problem_name = parse_problem_id(task_id)
    ProblemType = problem_types.get(type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{type}".')

    if not problem_name:
        raise Exception("No task name.")

    problem_instance = ProblemType(problem_name)
    problem_instance.validate_self()

    endpoint = None
    if replay:
        if replay.endswith(".pickle"):
            conversation = pickle.loads(Path(replay).read_bytes())
            endpoint = ReplayLLMEndpoint.from_conversation(conversation)
        elif replay.endswith(".json"):
            json_data = json.loads(Path(replay).read_text())
            conversation = Conversation.from_json(json_data)
            endpoint = ReplayLLMEndpoint.from_conversation(conversation)
        elif replay.endswith(".yaml"):
            raw_messages = yaml.load(Path(replay).read_text(), Loader=yaml.FullLoader)
            endpoint = ReplayLLMEndpoint.from_raw_messages(raw_messages)
        else:
            raise Exception("Unknown filetype for replay conversation.")
    else:
        endpoint = OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
        if not unsafe:
            silent = False
            endpoint = SafeguardLLMEndpoint(endpoint)

    conversation = None
    if resume:
        if resume.endswith(".pickle"):
            conversation = pickle.loads(Path(resume).read_bytes())
        elif resume.endswith(".json"):
            json_data = json.loads(Path(resume).read_text())
            conversation = Conversation.from_json(json_data)
        else:
            raise Exception("Unknown filetype for resume conversation.")
        if index:
            conversation = Conversation(conversation[:index])

    prompts = default_prompts
    loop = Loop(
        problem=problem_instance,
        endpoint=endpoint,
        prompts=prompts,
        enable_print=not silent,
        enable_log=not nologs,
        conversation=conversation,
    )

    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def parse_problem_id(problem_id: str) -> Tuple[str, str | None]:
    split = problem_id.split(":", maxsplit=1)
    if len(split) == 1:
        return (split[0], None)
    elif len(split) == 2:
        return (split[0], split[1])
    else:
        raise Exception
