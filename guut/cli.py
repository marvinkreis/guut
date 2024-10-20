import json
from collections import namedtuple
from pathlib import Path
from random import randbytes
from typing import Dict

import click
import yaml
from loguru import logger
from openai import OpenAI

from guut.baseline_loop import BaselineLoop, BaselineSettings
from guut.config import config
from guut.cosmic_ray import CosmicRayProblem, MultipleMutantsResult, list_mutants
from guut.cosmic_ray_runner import CosmicRayRunner
from guut.emse_benchmark import src_paths as emse_src_paths
from guut.formatting import format_problem
from guut.llm import Conversation, LLMEndpoint
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.logging import ConversationLogger, MessagePrinter
from guut.loop import Loop, LoopSettings, Result
from guut.output import StatusHelper, clean_filename, write_multiple_mutants_result_dir, write_result_dir
from guut.problem import Problem
from guut.quixbugs import QuixbugsProblem
from guut.quixbugs import list_problems as list_quixbugs_problems

problem_types = {QuixbugsProblem.get_type(): QuixbugsProblem}

GPT_MODEL = "gpt-4o-mini"


Preset = namedtuple("Preset", ["loop_cls", "loop_settings"])
SETTINGS_PRESETS: Dict[str, Preset] = {
    "debugging-one-shot": Preset(Loop, LoopSettings(preset_name="debugging_one_shot", include_example=True)),
    "debugging-zero-shot": Preset(Loop, LoopSettings(preset_name="debugging_zero_shot", include_example=False)),
    "baseline-with-iterations": Preset(
        BaselineLoop, BaselineSettings(preset_name="baseline_with_iterations", max_num_tests=10, max_num_turns=10)
    ),
    "baseline-without-iterations": Preset(
        BaselineLoop, BaselineSettings(preset_name="baseline_without_iterations", max_num_tests=1, max_num_turns=1)
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
    python_interpreter: str | None,
    unsafe: bool = False,
    silent: bool = False,
    nologs: bool = False,
    raw: bool = False,
):
    if replay and resume:
        raise Exception("Cannot use --replay and --continue together.")

    ctx.ensure_object(dict)
    ctx.obj["preset"] = preset
    ctx.obj["outdir"] = outdir
    ctx.obj["replay"] = replay
    ctx.obj["resume"] = resume
    ctx.obj["unsafe"] = unsafe
    ctx.obj["silent"] = silent
    ctx.obj["nologs"] = nologs
    ctx.obj["raw"] = raw
    ctx.obj["python_interpreter"] = python_interpreter


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
    outdir = Path(ctx.obj["outdir"]) if ctx.obj["outdir"] else config.output_path
    python_interpreter = (
        Path(ctx.obj["python_interpreter"]) if ctx.obj["python_interpreter"] else config.python_interpreter
    )

    problem = QuixbugsProblem(name, python_interpreter=python_interpreter)
    problem.validate_self()
    run_problem(problem, ctx, outdir)


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
    outdir = Path(ctx.obj["outdir"]) if ctx.obj["outdir"] else config.output_path
    python_interpreter = (
        Path(ctx.obj["python_interpreter"]) if ctx.obj["python_interpreter"] else config.python_interpreter
    )

    problem = CosmicRayProblem(
        module_path=Path(module_path),
        target_path=target_path,
        mutant_op_name=mutant_op,
        occurrence=occurrence,
        python_interpreter=python_interpreter,
    )
    problem.validate_self()
    run_problem(problem, ctx, outdir)


def _run_problem(
    problem: Problem,
    outdir: str | Path,
    conversation: Conversation | None,
    nologs: bool,
    silent: bool,
    raw: bool,
    endpoint: LLMEndpoint,
    preset_name: str,
    unsafe: bool,
) -> Result:
    preset = SETTINGS_PRESETS[preset_name]
    loop_cls = preset.loop_cls
    loop_settings = preset.loop_settings

    if not unsafe:
        endpoint = SafeguardLLMEndpoint(endpoint)

    conversation_logger = ConversationLogger() if not nologs else None
    message_printer = MessagePrinter(print_raw=raw) if not silent else None

    # TODO: solve this better
    prompts = problem.get_default_prompts()

    loop = loop_cls(
        problem=problem,
        endpoint=endpoint,
        prompts=prompts,
        printer=message_printer,
        logger=conversation_logger,
        conversation=conversation,
        settings=loop_settings,
    )

    result = loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")
    write_result_dir(result, out_dir=outdir)
    return result


def run_problem(problem: Problem, ctx: click.Context, outdir: str | Path):
    replay = ctx.obj["replay"]
    resume = ctx.obj["resume"]
    unsafe = ctx.obj["unsafe"]
    silent = ctx.obj["silent"]
    nologs = ctx.obj["nologs"]
    preset = ctx.obj["preset"]
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
            OpenAI(api_key=config.openai_api_key, organization=config.openai_organization), GPT_MODEL
        )

    conversation = None
    if resume:
        if resume.endswith(".json"):
            json_data = json.loads(Path(resume).read_text())
            conversation = Conversation.from_json(json_data)
        else:
            raise Exception("Unknown filetype for resume conversation.")

    _run_problem(
        problem=problem,
        outdir=outdir,
        conversation=conversation,
        nologs=nologs,
        silent=silent,
        raw=raw,
        endpoint=endpoint,
        preset_name=preset,
        unsafe=unsafe,
    )


@run.command("cosmic-ray-all-mutants")
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
@click.pass_context
def cosmic_ray_all_mutants(
    ctx: click.Context,
    session_file: str,
    module_path: str,
):
    unsafe = ctx.obj["unsafe"]
    silent = ctx.obj["silent"]
    nologs = ctx.obj["nologs"]
    raw = ctx.obj["raw"]
    preset = ctx.obj["preset"]

    outdir = Path(ctx.obj["outdir"]) if ctx.obj["outdir"] else config.output_path
    python_interpreter = (
        Path(ctx.obj["python_interpreter"]) if ctx.obj["python_interpreter"] else config.python_interpreter
    )

    endpoint = OpenAIEndpoint(OpenAI(api_key=config.openai_api_key, organization=config.openai_organization), GPT_MODEL)
    if not unsafe:
        silent = False
        endpoint = SafeguardLLMEndpoint(endpoint)

    conversation_logger = ConversationLogger() if not nologs else None
    message_printer = MessagePrinter(print_raw=raw) if not silent else None

    preset_ = SETTINGS_PRESETS[preset]
    loop_cls = preset_.loop_cls
    settings = preset_.loop_settings

    mutant_specs = list_mutants(Path(session_file))
    py = Path(python_interpreter) if python_interpreter else config.python_interpreter

    randchars = "".join(f"{b:02x}" for b in randbytes(4))
    id = "{}_{}_{}".format(preset, Path(module_path).stem, randchars)

    out_path = Path(outdir) / clean_filename(id)
    out_path.mkdir(parents=True, exist_ok=True)

    loops_dir = out_path / "loops"
    loops_dir.mkdir(exist_ok=True)

    status_helper = StatusHelper(id)
    runner = CosmicRayRunner(
        mutant_specs=mutant_specs,
        module_path=Path(module_path),
        python_interpreter=Path(py),
        endpoint=endpoint,
        loop_cls=loop_cls,
        conversation_logger=conversation_logger,
        message_printer=message_printer,
        loop_settings=settings,
    )

    status_helper.write_status(
        num_mutants=len(runner.mutants),
        num_queued=len(runner.mutant_queue),
        num_alive=len(runner.alive_mutants),
        num_killed=len(runner.killed_mutants),
    )
    status_helper.write_queue(queue=runner.mutant_queue)

    for result in runner.generate_tests(status_helper.write_problem_info):
        status_helper.write_status(
            num_mutants=len(runner.mutants),
            num_queued=len(runner.mutant_queue),
            num_alive=len(runner.alive_mutants),
            num_killed=len(runner.killed_mutants),
        )
        status_helper.write_queue(queue=runner.mutant_queue)
        write_result_dir(result, out_dir=loops_dir)

    write_multiple_mutants_result_dir(runner.get_result(), out_path)


def run_cosmic_ray_individual_mutants(
    ctx: click.Context, outdir: Path, python_interpreter: Path, module_path: Path, session_file: Path, id: str
):
    out_path = outdir / clean_filename(id)
    out_path.mkdir(parents=True, exist_ok=True)

    loops_dir = out_path / "loops"
    loops_dir.mkdir(exist_ok=True)

    mutants = list_mutants(Path(session_file))
    endpoint = OpenAIEndpoint(OpenAI(api_key=config.openai_api_key, organization=config.openai_organization), GPT_MODEL)

    status_helper = StatusHelper(id)
    queue = mutants
    killed_mutants = []
    alive_mutants = []
    tests = []

    status_helper.write_status(len(mutants), len(queue), len(alive_mutants), len(killed_mutants))
    status_helper.write_queue(queue=queue)

    while queue:
        mutant = queue.pop()
        logger.info(f"Preparing for {mutant}")
        problem = CosmicRayProblem(
            module_path=Path(module_path),
            target_path=mutant.target_path,
            mutant_op_name=mutant.mutant_op,
            occurrence=mutant.occurrence,
            python_interpreter=python_interpreter,
        )
        problem.validate_self()
        status_helper.write_problem_info(problem=problem)

        logger.info(f"Starting loop for {mutant}")
        result = _run_problem(
            problem=problem,
            outdir=loops_dir,
            conversation=None,
            nologs=ctx.obj["nologs"],
            silent=ctx.obj["silent"],
            raw=ctx.obj["raw"],
            endpoint=endpoint,
            preset_name=ctx.obj["preset"],
            unsafe=ctx.obj["unsafe"],
        )

        if result.mutant_killed:
            logger.info(f"Loop killed mutant {mutant}")
            killed_mutants.append(mutant)
            tests.append((result.long_id, result.get_killing_test()))
        else:
            logger.info(f"Loop failed to kill mutant {mutant}")
            alive_mutants.append(mutant)

        status_helper.write_status(len(mutants), len(queue), len(alive_mutants), len(killed_mutants))

    write_multiple_mutants_result_dir(
        MultipleMutantsResult(mutants=mutants, alive_mutants=alive_mutants, killed_mutants=killed_mutants, tests=tests),
        out_path,
    )


@run.command("cosmic-ray-individual-mutants")
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
@click.pass_context
def cosmic_ray_individual_mutants(
    ctx: click.Context,
    session_file: str,
    module_path: str,
):
    outdir = Path(ctx.obj["outdir"]) if ctx.obj["outdir"] else config.output_path
    python_interpreter = (
        Path(ctx.obj["python_interpreter"]) if ctx.obj["python_interpreter"] else config.python_interpreter
    )

    randchars = "".join(f"{b:02x}" for b in randbytes(4))
    id = "{}_{}_{}".format(ctx.obj["preset"], Path(module_path).stem, randchars)

    run_cosmic_ray_individual_mutants(
        ctx=ctx,
        outdir=outdir,
        python_interpreter=python_interpreter,
        module_path=Path(module_path),
        session_file=Path(session_file),
        id=id,
    )


@run.command("emse-project-individual-mutants")
@click.argument(
    "project_name",
    nargs=1,
    type=str,
    required=True,
)
@click.pass_context
def emse_project(
    ctx: click.Context,
    project_name: str,
):
    outdir = Path(ctx.obj["outdir"]) if ctx.obj["outdir"] else config.output_path
    python_interpreter = Path(ctx.obj["python_interpreter"]) if ctx.obj["python_interpreter"] else None

    if project_name not in emse_src_paths:
        raise Exception("Unknown emse project name.")

    project_path = config.emse_projects_path / project_name
    module_path = project_path / emse_src_paths[project_name]
    session_file = config.emse_projects_path / f"{project_name}.sqlite"

    if python_interpreter is None:
        python_interpreter = project_path / ".venv" / "bin" / "python"

    randchars = "".join(f"{b:02x}" for b in randbytes(4))
    id = "{}_{}_{}".format(ctx.obj["preset"], project_name, randchars)

    run_cosmic_ray_individual_mutants(
        ctx=ctx,
        outdir=outdir,
        python_interpreter=python_interpreter,
        module_path=Path(module_path),
        session_file=Path(session_file),
        id=id,
    )
