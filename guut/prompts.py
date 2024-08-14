from dataclasses import dataclass
from pathlib import Path
from typing import List

import jinja2

from guut.execution import ExperimentResult
from guut.formatting import add_line_numbers, format_debugger_result, format_test_result
from guut.llm import SystemMessage, UserMessage
from guut.problem import Problem

templates_path = Path(__file__).parent.parent / "templates"
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_path), trim_blocks=True)
jinja_env.filters["format_test_result"] = format_test_result
jinja_env.filters["format_debugger_result"] = format_debugger_result
jinja_env.filters["add_line_numbers"] = add_line_numbers
jinja_env.filters["rtrim"] = lambda s: s.rstrip()


class SystemPrompt:
    def __init__(self, template_path: str):
        self.template = jinja_env.get_template(template_path)

    def render(self) -> SystemMessage:
        return SystemMessage(self.template.render().strip() + "\n")


class DebugPrompt:
    def __init__(self, template_path: str, stop_words: List[str]):
        self.template = jinja_env.get_template(template_path)
        self.stop_words = stop_words

    def render(self, problem: Problem) -> UserMessage:
        return UserMessage(self.template.render().strip() + "\n")

    def get_stop_words(self) -> List[str]:
        return self.stop_words


class ProblemTemplate:
    def __init__(self, template_path: str):
        self.template = jinja_env.get_template(template_path)

    def render(self, problem: Problem) -> UserMessage:
        return UserMessage(
            self.template.render(
                problem=problem,
            ).strip()
            + "\n"
        )


class ExperimentResultsTemplate:
    def __init__(self, template_path: str):
        self.template = jinja_env.get_template(template_path)

    def render(self, result: ExperimentResult) -> UserMessage:
        return UserMessage(self.template.render(result=result).strip() + "\n")


class TestResultsTemplate:
    pass


class TestPrompt:
    def __init__(self, template_path: str, stop_words: List[str]):
        self.template = jinja_env.get_template(template_path)
        self.stop_words = stop_words

    def render(self, max_iterations: bool) -> UserMessage:
        return UserMessage(self.template.render(max_iterations=max_iterations).strip() + "\n")

    def get_stop_words(self) -> List[str]:
        return self.stop_words


@dataclass
class PromptCollection:
    system_prompt: SystemPrompt | None
    debug_prompt: DebugPrompt
    test_prompt: TestPrompt
    experiment_results_template: ExperimentResultsTemplate
    problem_template: ProblemTemplate


system_prompt = SystemPrompt("prompts/system_prompt.md")
debug_prompt = DebugPrompt("prompts/debug_prompt.md", ["Experiment Result", "Experiment Output", "<DEBUGGING_DONE>"])
test_prompt = TestPrompt("prompts/test_prompt.md", [])
experiment_results_template = ExperimentResultsTemplate("experiment_results_template.md")
problem_template = ProblemTemplate("problem_template.md")
