import json
from collections import namedtuple
from pathlib import Path
from random import randbytes
from typing import Dict

import click
import yaml
from baseline_loop import BaselineLoop
from loguru import logger
from openai import OpenAI

from guut.config import config
from guut.cosmic_ray import CosmicRayProblem, list_mutants
from guut.cosmic_ray_runner import CosmicRayRunner
from guut.formatting import format_problem
from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.logging import ConversationLogger, MessagePrinter
from guut.loop import Loop, LoopSettings
from guut.output import CustomJSONEncoder, write_cosmic_ray_runner_result_dir, write_result_dir
from guut.problem import Problem
from guut.quixbugs import QuixbugsProblem
from guut.quixbugs import list_problems as list_quixbugs_problems

problem_types = {QuixbugsProblem.get_type(): QuixbugsProblem}


Preset = namedtuple("Preset", ["loop_cls", "loop_settings"])
SETTINGS_PRESETS: Dict[str, Preset] = {
    "debugging_one_shot": Preset(Loop, LoopSettings(name="debugging_one_shot", include_example=True)),
    "debugging_zero_shot": Preset(Loop, LoopSettings(name="debugging_zero_shot", include_example=False)),
    "baseline_with_iterations": Preset(
        BaselineLoop, LoopSettings(name="baseline_with_iterations", max_retries_for_invalid_test=9)
    ),
    "baseline_without_iterations": Preset(
        BaselineLoop, LoopSettings("baseline_without_iterations", max_retries_for_invalid_test=0)
    ),
}
SETTINGS_PRESETS_KEYS = list(SETTINGS_PRESETS.keys())


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
@click.option("--raw", is_flag=True, default=False, help="Print messages as raw text.")
@click.option(
    "--python-interpreter",
    "--py",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="The python interpreter to use for testing.",
)
@click.option(
    "--preset",
    nargs=1,
    type=click.Choice(SETTINGS_PRESETS_KEYS),
    required=True,
    help="The preset to use.",
)
@click.pass_context
def run(
    ctx,
    preset: str,
    outdir: str | None,
    replay: str | None,
    resume: str | None,
    index: int | None,
    python_interpreter: str | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
    raw: bool = False,
):
    if replay and resume:
        raise Exception("Cannot use --replay and --continue together.")
    if index and not resume:
        raise Exception("Cannot use --index without --continue.")

    ctx.ensure_object(dict)
    ctx.obj["preset"] = preset
    ctx.obj["outdir"] = outdir
    ctx.obj["replay"] = replay
    ctx.obj["resume"] = resume
    ctx.obj["index"] = index
    ctx.obj["unsafe"] = unsafe
    ctx.obj["silent"] = silent
    ctx.obj["nologs"] = nologs
    ctx.obj["raw"] = raw
    py = Path(python_interpreter) if python_interpreter else config.python_interpreter
    ctx.obj["python_interpreter"] = py


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
def run_quixbugs(ctx: click.Context, name: str):
    problem = QuixbugsProblem(name)
    problem.validate_self()
    run_problem(problem, ctx)


@list.command("cosmic-ray")
@click.argument("session_file", nargs=1, type=click.Path(dir_okay=False), required=True)
def list_cosmic_ray(session_file: str):
    mutants = list_mutants(Path(session_file))
    target_path_len = max(6, max(len(m.target_path) for m in mutants))
    mutant_op_len = max(9, max(len(m.mutant_op) for m in mutants))
    occurrence_len = max(1, max(len(str(m.occurrence)) for m in mutants))
    line_len = max(4, max(len(str(m.line_start)) for m in mutants))

    print(
        f"{"target":<{target_path_len}}  {"mutant_op":<{mutant_op_len}}  {"#":<{occurrence_len}}  {"line":<{line_len}}"
    )
    print("-" * (target_path_len + mutant_op_len + occurrence_len + line_len + 6))
    for m in mutants:
        print(
            f"{m.target_path:<{target_path_len}}  {m.mutant_op:<{mutant_op_len}}  {m.occurrence:<{occurrence_len}}  {m.line_start:<{line_len}}"
        )


@show.command("cosmic-ray")
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


@run.command("cosmic-ray")
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
    ctx: click.Context,
    module_path: str,
    target_path: str,
    mutant_op: str,
    occurrence: int,
):
    problem = CosmicRayProblem(
        module_path=Path(module_path),
        target_path=target_path,
        mutant_op_name=mutant_op,
        occurrence=occurrence,
        python_interpreter=ctx.obj["python_interpreter"],
    )
    problem.validate_self()
    run_problem(problem, ctx)


def run_problem(problem: Problem, ctx: click.Context):
    outdir = ctx.obj["outdir"]
    replay = ctx.obj["replay"]
    resume = ctx.obj["resume"]
    index = ctx.obj["index"]
    unsafe = ctx.obj["unsafe"]
    silent = ctx.obj["silent"]
    nologs = ctx.obj["nologs"]
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

    preset = SETTINGS_PRESETS[ctx.obj["preset"]]
    LoopCls = preset.loop_cls
    settings = preset.loop_settings

    # TODO: solve this better
    prompts = problem.get_default_prompts()

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


# TODO: add python interpreter
@cli.command()
@click.argument(
    "session_file",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.argument(
    "module_path",
    nargs=1,
    type=click.Path(exists=True, file_okay=False),
    required=True,
)
@click.option(
    "--outdir",
    nargs=1,
    type=click.Path(exists=True, file_okay=False),
    required=False,
    help="Write results to the given directory. Otherwise the working directory is used.",
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
@click.option("--raw", is_flag=True, default=False, help="Print messages as raw text.")
@click.option(
    "--python-interpreter",
    "--py",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="The python interpreter to use for testing.",
)
@click.option(
    "--preset",
    nargs=1,
    type=click.Choice(SETTINGS_PRESETS_KEYS),
    required=True,
    help="The preset to use.",
)
def cosmic_ray_runner(
    session_file: str,
    module_path: str,
    preset: str,
    outdir: str | None,
    python_interpreter: str | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
    raw: bool = False,
):
    endpoint = None
    endpoint = OpenAIEndpoint(
        OpenAI(api_key=config.openai_api_key, organization=config.openai_organization), "gpt-4o-mini"
    )
    if not unsafe:
        silent = False
        endpoint = SafeguardLLMEndpoint(endpoint)

    conversation_logger = ConversationLogger() if not nologs else None
    message_printer = MessagePrinter(print_raw=raw) if not silent else None

    preset_ = SETTINGS_PRESETS[preset]
    LoopCls = preset_.loop_cls
    settings = preset_.loop_settings

    mutant_specs = list_mutants(Path(session_file))
    py = Path(python_interpreter) if python_interpreter else config.python_interpreter

    out_path = Path(outdir) if outdir else config.output_path

    randchars = "".join(f"{b:02x}" for b in randbytes(4))
    id = "{}_{}".format(Path(module_path).stem, randchars)

    out_path = out_path / id
    out_path.mkdir(parents=True, exist_ok=True)

    loops_dir = out_path / "loops"
    loops_dir.mkdir(exist_ok=True)

    runner = CosmicRayRunner(
        mutant_specs=mutant_specs,
        module_path=Path(module_path),
        python_interpreter=Path(py),
        endpoint=endpoint,
        loop_cls=LoopCls,
        conversation_logger=conversation_logger,
        message_printer=message_printer,
        loop_settings=settings,
    )

    import json

    Path("/tmp/guut").mkdir(exist_ok=True)

    for result in runner.generate_tests():
        Path("/tmp/guut/status.txt").write_text(
            f"total: {len(runner.mutants)}\nqueued: {len(runner.mutant_queue)}\nalive: {len(runner.alive_mutants)}\nkilled: {len(runner.killed_mutants)}"
        )
        with Path("/tmp/guut/queue.json").open("w") as f:
            json.dump(runner.mutant_queue, f, cls=CustomJSONEncoder)
        write_result_dir(result, out_dir=loops_dir)

    write_cosmic_ray_runner_result_dir(runner.get_result(), out_path)
