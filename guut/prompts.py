from dataclasses import dataclass, replace
from pathlib import Path
from typing import List

import jinja2

import guut.formatting as formatting
from guut.llm import SystemMessage, UserMessage
from guut.problem import AltExperimentResult, ExperimentResult, Problem, TestResult, ValidationResult

templates_path = Path(__file__).parent.parent / "templates"
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_path), trim_blocks=True)
jinja_env.filters["format_test_result"] = formatting.format_execution_result
jinja_env.filters["format_debugger_result"] = formatting.format_execution_result
jinja_env.filters["format_validation_result"] = formatting.format_validation_result
jinja_env.filters["add_line_numbers"] = formatting.add_line_numbers
jinja_env.filters["rtrim"] = lambda s: s.rstrip()
jinja_env.filters["limit_text"] = formatting.limit_text
jinja_env.filters["get_import_path"] = formatting.get_import_path
jinja_env.filters["get_module_name"] = formatting.get_module_name


class Template:
    def __init__(self, template_path: str):
        self.path = template_path
        self.template = jinja_env.get_template(template_path)


class SystemPrompt(Template):
    def render(self) -> SystemMessage:
        return SystemMessage(self.template.render().strip() + "\n")


class DebugPrompt(Template):
    def render(self, problem: Problem, include_equivalence: bool = True, shortexp: bool = False) -> UserMessage:
        return UserMessage(
            self.template.render(problem=problem, include_equivalence=include_equivalence, shortexp=shortexp).strip()
            + "\n"
        )


class ProblemTemplate(Template):
    def render(self, problem: Problem, is_baseline: bool = False) -> UserMessage:
        return UserMessage(self.template.render(problem=problem, is_baseline=is_baseline).strip() + "\n")


class ExperimentDoesntCompileTemplate(Template):
    def render(self, result: ValidationResult, name: str) -> UserMessage:
        return UserMessage(self.template.render(result=result, name=name).strip() + "\n")


class ExperimentResultsTemplate(Template):
    def render(
        self, result: ExperimentResult | AltExperimentResult, name: str, altexp: bool, shortexp: bool
    ) -> UserMessage:
        return UserMessage(
            self.template.render(result=result, name=name, altexp=altexp, shortexp=shortexp).strip() + "\n"
        )


class TestPrompt(Template):
    def render(self, max_experiments_reached: bool, num_turns_left: int) -> UserMessage:
        return UserMessage(
            self.template.render(max_experiments_reached=max_experiments_reached, num_turns_left=num_turns_left).strip()
            + "\n"
        )


class TestDoesntCompileTemplate(Template):
    def render(self, result: ValidationResult) -> UserMessage:
        return UserMessage(self.template.render(result=result).strip() + "\n")


class TestDoesntDetectMutantTemplate(Template):
    def render(self, result: TestResult, baseline: bool, no_asserts: bool) -> UserMessage:
        return UserMessage(self.template.render(result=result, baseline=baseline, no_asserts=no_asserts).strip() + "\n")


class ResultsTemplate(Template):
    def render_for_test(self, test: str, result: TestResult, problem: Problem) -> UserMessage:
        return UserMessage(self.template.render(test=test, result=result, problem=problem).strip() + "\n")

    def render_for_equivalence(self, problem: Problem) -> UserMessage:
        return UserMessage(
            self.template.render(test=None, result=None, claimed_equivalent=True, problem=problem).strip() + "\n"
        )


class ConversationAbortedTemplate(Template):
    def render(self, reason: str, extra_reason: str | None = None) -> UserMessage:
        return UserMessage(self.template.render(reason=reason, extra_reason=extra_reason).strip() + "\n")


class IncompleteResponseTemplate(Template):
    def render(self) -> UserMessage:
        return UserMessage(self.template.render().strip() + "\n")


class BaselinePrompt(Template):
    def render(self, problem: Problem, include_equivalence: bool = True) -> UserMessage:
        return UserMessage(
            self.template.render(problem=problem, include_equivalence=include_equivalence).strip() + "\n"
        )


class EquivalenceClaimTemplate(Template):
    def render(self) -> UserMessage:
        return UserMessage(self.template.render().strip() + "\n")


@dataclass
class PromptCollection:
    system_prompt: SystemPrompt | None
    debug_prompt: DebugPrompt
    test_prompt: TestPrompt
    baseline_prompt: BaselinePrompt

    stop_words: List[str]
    baseline_stop_words: List[str]

    problem_template: ProblemTemplate
    experiment_doesnt_compile_template: ExperimentDoesntCompileTemplate
    experiment_results_template: ExperimentResultsTemplate
    test_doesnt_compile_template: TestDoesntCompileTemplate
    test_doesnt_detect_mutant_template: TestDoesntDetectMutantTemplate
    equivalence_claim_template: EquivalenceClaimTemplate

    results_template: ResultsTemplate
    conversation_aborted_template: ConversationAbortedTemplate
    incomplete_response_template: IncompleteResponseTemplate

    def replace(self, **kwargs):
        return replace(self, **kwargs)


default_prompts = PromptCollection(
    system_prompt=SystemPrompt("system_prompt.md"),
    debug_prompt=DebugPrompt("debug_prompt.md"),
    test_prompt=TestPrompt("test_prompt.md"),
    baseline_prompt=BaselinePrompt("baseline_prompt.md"),
    #
    stop_words=["# Experiment Result", "# Test Result", "# Observation Result"],
    baseline_stop_words=["# Test Result"],
    #
    problem_template=ProblemTemplate("problem_template.md"),
    experiment_doesnt_compile_template=ExperimentDoesntCompileTemplate("experiment_doesnt_compile_template.md"),
    experiment_results_template=ExperimentResultsTemplate("experiment_results_template.md"),
    test_doesnt_compile_template=TestDoesntCompileTemplate("test_doesnt_compile_template.md"),
    test_doesnt_detect_mutant_template=TestDoesntDetectMutantTemplate("test_doesnt_detect_mutant_template.md"),
    results_template=ResultsTemplate("results_template.md"),
    conversation_aborted_template=ConversationAbortedTemplate("conversation_aborted_template.md"),
    incomplete_response_template=IncompleteResponseTemplate("incomplete_response_template.md"),
    equivalence_claim_template=EquivalenceClaimTemplate("equivalence_claim_template.md"),
)

debug_prompt_altexp = DebugPrompt("debug_prompt_altexp.md")
debug_prompt_new = DebugPrompt("debug_prompt_new.md")
