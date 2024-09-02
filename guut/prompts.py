from dataclasses import dataclass, replace
from pathlib import Path
from typing import List

import jinja2

import guut.formatting as formatting
from guut.llm import SystemMessage, UserMessage
from guut.problem import ExperimentResult, Problem, TestResult, ValidationResult

templates_path = Path(__file__).parent.parent / "templates"
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_path), trim_blocks=True)
jinja_env.filters["format_test_result"] = formatting.format_execution_result
jinja_env.filters["format_debugger_result"] = formatting.format_execution_result
jinja_env.filters["add_line_numbers"] = formatting.add_line_numbers
jinja_env.filters["rtrim"] = lambda s: s.rstrip()
jinja_env.filters["limit_text"] = formatting.limit_text


class Template:
    def __init__(self, template_path: str):
        self.path = template_path
        self.template = jinja_env.get_template(template_path)


class SystemPrompt(Template):
    def render(self) -> SystemMessage:
        return SystemMessage(self.template.render().strip() + "\n")


class DebugPrompt(Template):
    def render(self, problem: Problem) -> UserMessage:
        return UserMessage(self.template.render().strip() + "\n")


class ProblemTemplate(Template):
    def render(self, problem: Problem) -> UserMessage:
        return UserMessage(self.template.render(problem=problem).strip() + "\n")


class ExperimentDoesntCompileTemplate(Template):
    def render(self, result: ValidationResult) -> UserMessage:
        return UserMessage(self.template.render(result=result).strip() + "\n")


class ExperimentResultsTemplate(Template):
    def render(self, result: ExperimentResult, is_observation: bool = False) -> UserMessage:
        return UserMessage(self.template.render(result=result, is_observation=is_observation).strip() + "\n")


class TestPrompt(Template):
    def render(self, max_iterations: bool) -> UserMessage:
        return UserMessage(self.template.render(max_iterations=max_iterations).strip() + "\n")


class TestDoesntCompileTemplate(Template):
    def render(self, result: ValidationResult) -> UserMessage:
        return UserMessage(self.template.render(result=result).strip() + "\n")


class TestDoesntDetectMutantTemplate(Template):
    def render(self, result: TestResult) -> UserMessage:
        return UserMessage(self.template.render(result=result).strip() + "\n")


class ResultsTemplate(Template):
    def render(self, test: str, result: TestResult) -> UserMessage:
        return UserMessage(self.template.render(test=test, result=result).strip() + "\n")


class ConversationAbortedTemplate(Template):
    def render(self, reason: str, extra_reason: str | None = None) -> UserMessage:
        return UserMessage(self.template.render(reason=reason, extra_reason=extra_reason).strip() + "\n")


class IncompleteResponseTemplate(Template):
    def render(self) -> UserMessage:
        return UserMessage(self.template.render().strip() + "\n")


@dataclass
class PromptCollection:
    system_prompt: SystemPrompt | None
    debug_prompt: DebugPrompt
    test_prompt: TestPrompt

    stop_words: List[str]

    problem_template: ProblemTemplate
    experiment_doesnt_compile_template: ExperimentDoesntCompileTemplate
    experiment_results_template: ExperimentResultsTemplate
    test_doesnt_compile_template: TestDoesntCompileTemplate
    test_doesnt_detect_mutant_template: TestDoesntDetectMutantTemplate

    results_template: ResultsTemplate
    conversation_aborted_template: ConversationAbortedTemplate
    incomplete_response_template: IncompleteResponseTemplate

    def replace(self, **kwargs):
        return replace(self, **kwargs)


default_prompts = PromptCollection(
    system_prompt=SystemPrompt("prompts/system_prompt.md"),
    debug_prompt=DebugPrompt("prompts/debug_prompt.md"),
    test_prompt=TestPrompt("prompts/test_prompt.md"),
    #
    stop_words=["# Experiment Result", "# Test Result", "# Observation Result"],
    #
    problem_template=ProblemTemplate("problem_template.md"),
    experiment_doesnt_compile_template=ExperimentDoesntCompileTemplate("experiment_doesnt_compile_template.md"),
    experiment_results_template=ExperimentResultsTemplate("experiment_results_template.md"),
    test_doesnt_compile_template=TestDoesntCompileTemplate("test_doesnt_compile_template.md"),
    test_doesnt_detect_mutant_template=TestDoesntDetectMutantTemplate("test_doesnt_detect_mutant_template.md"),
    results_template=ResultsTemplate("results_template.md"),
    conversation_aborted_template=ConversationAbortedTemplate("conversation_aborted_template.md"),
    incomplete_response_template=IncompleteResponseTemplate("incomplete_response_template.md"),
)
