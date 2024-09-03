import json
import pickle
from pathlib import Path

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
from guut.output import write_result_dir
from guut.quixbugs import QuixbugsProblem
from tests.loop_test import LoopSettings

problem_types = {"quixbugs": QuixbugsProblem}


@click.group()
def main():
    pass


@main.command(
    "list",
    short_help="Lists task types. Lists tasks. Shows tasks.",
    help="Use 'list' to list task types. Use 'list <type>' to list tasks of that type. Use 'list <type> <args>' to show a task.",
)
@click.argument("task_type", nargs=1, type=str, required=False)
@click.argument("task_args", nargs=1, type=str, required=False)
def _list(task_type: str | None, task_args: str | None):
    if not task_type:
        for type in problem_types.keys():
            print(type)
        return

    if not task_args:
        list_tasks(task_type)
        return

    show_task(task_type, task_args)


def list_tasks(type: str):
    ProblemType = problem_types.get(type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{type}".')

    problems = ProblemType.list_problems()
    for args in problems:
        if " " in args:
            print(f'"{args}"')
        else:
            print(args)


def show_task(type: str, problem_description: str):
    ProblemType = problem_types.get(type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{type}".')
    if not problem_description:
        raise Exception()

    problem = ProblemType(problem_description)
    print(format_problem(problem))


@main.command()
@click.argument("task_type", nargs=1, type=str, required=True)
@click.argument("task_args", nargs=1, type=str, required=True)
@click.option(
    "--outdir",
    nargs=1,
    type=click.Path(exists=True, file_okay=False),
    required=False,
    help="Write results to the given directory. Otherwise the working directory is used.",
)
@click.option(
    "--replay",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Replay LLM responses instead of requesting completions. Path can be a logged .pickle or .json conversation log or a .yaml file containing a list of strings. Implies -y.",
)
@click.option(
    "--continue",
    "resume",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Continue a conversation from a .pickle or .json log file.",
)
@click.option(
    "--index",
    "-n",
    nargs=1,
    type=int,
    required=False,
    help="Use with --continue. Selects the number of messages to pick from the conversation (including messages of all roles). Use negative numbers to exclude messages starting from the end.",
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
@click.option("--nologs", "-n", is_flag=True, default=False, help="Disable logging of conversations.")
def run(
    task_type: str,
    task_args: str,
    outdir: str | None,
    replay: str | None,
    resume: str | None,
    index: int | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
):
    if replay and resume:
        raise Exception("Cannot use --replay and --continue together.")
    if index and not resume:
        raise Exception("Cannot use --index without --continue.")

    ProblemType = problem_types.get(task_type)
    if not ProblemType:
        raise Exception(f'Unknown task type: "{task_type}".')

    problem_instance = ProblemType(task_args)
    problem_instance.validate_self()

    endpoint = None
    if replay:
        if replay.endswith(".pickle"):
            conversation = pickle.loads(Path(replay).read_bytes())
            endpoint = ReplayLLMEndpoint.from_conversation(conversation, path=replay, replay_file=Path(replay))
        elif replay.endswith(".json"):
            json_data = json.loads(Path(replay).read_text())
            conversation = Conversation.from_json(json_data)
            endpoint = ReplayLLMEndpoint.from_conversation(conversation, path=replay, replay_file=Path(replay))
        elif replay.endswith(".yaml"):
            raw_messages = yaml.load(Path(replay).read_text(), Loader=yaml.FullLoader)
            endpoint = ReplayLLMEndpoint.from_raw_messages(raw_messages, path=replay, replay_file=Path(replay))
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

    loop = Loop(
        problem=problem_instance,
        endpoint=endpoint,
        prompts=problem_instance.get_default_prompts(),
        enable_print=not silent,
        enable_log=not nologs,
        conversation=conversation,
        settings=LoopSettings(),
    )

    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")

    result = loop.get_result()
    write_result_dir(result, out_dir=outdir)
