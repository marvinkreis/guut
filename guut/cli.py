import json
from dataclasses import replace
from pathlib import Path

import click
import yaml
from loguru import logger
from openai import OpenAI

from guut.baseline_loop import BaselineLoop, BaselineSettings
from guut.config import config
from guut.cosmic_ray import CosmicRayProblem, list_mutants
from guut.formatting import format_problem
from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.logging import ConversationLogger, MessagePrinter
from guut.loop import Loop, LoopSettings
from guut.output import write_result_dir
from guut.problem import Problem
from guut.prompts import debug_prompt_altexp
from guut.quixbugs import QuixbugsProblem
from guut.quixbugs import list_problems as list_quixbugs_problems

problem_types = {QuixbugsProblem.get_type(): QuixbugsProblem}


@click.group()
def cli():
    pass


@cli.group()
def list():
    pass


@cli.group()
def show():
    pass


@cli.group()
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
    help="Replay LLM responses instead of requesting completions. Path can be a logged .json conversation log or a .yaml file containing a list of strings. Implies -y.",
)
@click.option(
    "--continue",
    "resume",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Continue a conversation from a .json log file.",
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
@click.option("--silent", "-s", is_flag=True, default=False, help="Disable the printing of new messages.")
@click.option("--nologs", "-n", is_flag=True, default=False, help="Disable the logging of conversations.")
@click.option("--baseline", "-b", is_flag=True, default=False, help="Use baseline instead of regular loop.")
@click.option("--altexp", "-a", is_flag=True, default=False, help="Use the alterenative experiment format.")
@click.option("--shortexp", is_flag=True, default=False, help="Include only debugger output if debugger is used.")
@click.pass_context
def run(
    ctx,
    outdir: str | None,
    replay: str | None,
    resume: str | None,
    index: int | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
    baseline: bool = False,
    altexp: bool = False,
    shortexp: bool = False,
    raw: bool = False,
):
    if replay and resume:
        raise Exception("Cannot use --replay and --continue together.")
    if index and not resume:
        raise Exception("Cannot use --index without --continue.")

    ctx.ensure_object(dict)
    ctx.obj["outdir"] = outdir
    ctx.obj["replay"] = replay
    ctx.obj["resume"] = resume
    ctx.obj["index"] = index
    ctx.obj["unsafe"] = unsafe
    ctx.obj["silent"] = silent
    ctx.obj["nologs"] = nologs
    ctx.obj["baseline"] = baseline
    ctx.obj["altexp"] = altexp
    ctx.obj["shortexp"] = shortexp
    ctx.obj["raw"] = raw


@list.command("quixbugs")
def list_quixbugs():
    for name in list_quixbugs_problems():
        print(name)


@show.command("quixbugs")
@click.argument("name", nargs=1, type=str, required=True)
def show_quixbugs(name: str):
    problem = QuixbugsProblem(name)
    problem.validate_self()
    print(format_problem(problem))


@run.command("quixbugs")
@click.argument("name", nargs=1, type=str, required=True)
@click.pass_context
def run_quixbugs(ctx, name: str):
    problem = QuixbugsProblem(name)
    problem.validate_self()
    run_problem(problem, ctx)


@list.command("cosmic_ray")
@click.argument("session_file", nargs=1, type=click.Path(dir_okay=False), required=True)
def list_cosmic_ray(session_file: Path):
    mutants = list_mutants(session_file)
    module_path_len = max(6, max(len(m.module_path) for m in mutants))
    mutant_op_len = max(9, max(len(m.mutant_op) for m in mutants))
    occurrence_len = max(1, max(len(str(m.occurrence)) for m in mutants))
    line_len = max(4, max(len(str(m.line_start)) for m in mutants))

    print(
        f"{"target":<{module_path_len}}  {"mutant_op":<{mutant_op_len}}  {"#":<{occurrence_len}}  {"line":<{line_len}}"
    )
    print("-" * (module_path_len + mutant_op_len + occurrence_len + line_len + 6))
    for m in mutants:
        print(
            f"{m.module_path:<{module_path_len}}  {m.mutant_op:<{mutant_op_len}}  {m.occurrence:<{occurrence_len}}  {m.line_start:<{line_len}}"
        )


@show.command("cosmic_ray")
@click.argument(
    "module_path",
    nargs=1,
    type=click.Path(exists=True),
    required=True,
)
@click.argument(
    "target_path",
    nargs=1,
    type=str,
    required=True,
)
@click.argument(
    "mutant_op",
    nargs=1,
    type=str,
    required=True,
)
@click.argument(
    "occurrence",
    nargs=1,
    type=int,
    required=True,
)
def show_cosmic_ray(module_path: str, target_path: str, mutant_op: str, occurrence: int):
    problem = CosmicRayProblem(
        module_path=Path(module_path), target_path=target_path, mutant_op_name=mutant_op, occurrence=occurrence
    )
    problem.validate_self()
    print(format_problem(problem))


@run.command("cosmic_ray")
@click.argument(
    "module_path",
    nargs=1,
    type=click.Path(exists=True),
    required=True,
)
@click.argument(
    "target_path",
    nargs=1,
    type=str,
    required=True,
)
@click.argument(
    "mutant_op",
    nargs=1,
    type=str,
    required=True,
)
@click.argument(
    "occurrence",
    nargs=1,
    type=int,
    required=True,
)
@click.pass_context
def run_cosmic_ray(
    ctx,
    module_path: Path,
    target_path: str,
    mutant_op: str,
    occurrence: int,
):
    problem = CosmicRayProblem(
        module_path=module_path, target_path=target_path, mutant_op_name=mutant_op, occurrence=occurrence
    )
    problem.validate_self()
    run_problem(problem, ctx)


def run_problem(problem: Problem, ctx):
    outdir = ctx.obj["outdir"]
    replay = ctx.obj["replay"]
    resume = ctx.obj["resume"]
    index = ctx.obj["index"]
    unsafe = ctx.obj["unsafe"]
    silent = ctx.obj["silent"]
    nologs = ctx.obj["nologs"]
    baseline = ctx.obj["baseline"]
    altexp = ctx.obj["altexp"]
    shortexp = ctx.obj["shortexp"]
    raw = ctx.obj["raw"]

    endpoint = None
    if replay:
        if replay.endswith(".json"):
            json_data = json.loads(Path(replay).read_text())
            conversation = Conversation.from_json(json_data)
            endpoint = ReplayLLMEndpoint.from_conversation(conversation, path=replay, replay_file=Path(replay))
        elif replay.endswith(".yaml"):
            raw_messages = yaml.load(Path(replay).read_text(), Loader=yaml.FullLoader)
            endpoint = ReplayLLMEndpoint.from_raw_messages(raw_messages, path=replay, replay_file=Path(replay))
        else:
            raise Exception("Unknown filetype for replay conversation.")
    else:
        endpoint = OpenAIEndpoint(
            OpenAI(api_key=config.openai_api_key, organization=config.openai_organization), "gpt-4o-mini"
        )
        if not unsafe:
            silent = False
            endpoint = SafeguardLLMEndpoint(endpoint)

    conversation = None
    if resume:
        if resume.endswith(".json"):
            json_data = json.loads(Path(resume).read_text())
            conversation = Conversation.from_json(json_data)
        else:
            raise Exception("Unknown filetype for resume conversation.")
        if index:
            conversation = Conversation(conversation[:index])

    conversation_logger = ConversationLogger() if not nologs else None
    message_printer = MessagePrinter(print_raw=raw) if not silent else None

    LoopCls = Loop if not baseline else BaselineLoop
    settings = LoopSettings() if not baseline else BaselineSettings()
    settings = replace(settings, altexp=altexp, shortexp=shortexp)

    # TODO: solve this better
    prompts = problem.get_default_prompts()
    if altexp:
        prompts = prompts.replace(debug_prompt=debug_prompt_altexp)

    loop = LoopCls(
        problem=problem,
        endpoint=endpoint,
        prompts=prompts,
        printer=message_printer,
        logger=conversation_logger,
        conversation=conversation,
        settings=settings,
    )

    result = loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")
    write_result_dir(result, out_dir=outdir or config.output_path)
