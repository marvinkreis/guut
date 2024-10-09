from typing import Tuple, override

from guut.llm import AssistantMessage
from guut.loop import (
    EquivalenceClaim,
    ExperimentDescription,
    InvalidStateException,
    Loop,
    LoopSettings,
    Response,
    Result,
    State,
    TestDescription,
)


class BaselineSettings(LoopSettings):
    @override
    def __init__(
        self,
        name: str,
        max_num_experiments: int = 0,
        max_retries_for_invalid_test: int = 99,
        max_num_incomplete_responses: int = 2,
        max_num_turns: int = 10,
        test_inctructions_after_turn: int = 99,
        is_baseline=True,
    ):
        super().__init__(
            name=name,
            max_num_experiments=0,
            max_retries_for_invalid_test=max_retries_for_invalid_test,
            max_num_incomplete_responses=max_num_incomplete_responses,
            max_num_turns=max_num_turns,
            test_inctructions_after_turn=test_inctructions_after_turn,
            include_example=False,
            is_baseline=True,
        )


class BaselineReponse(Response):
    def __init__(self, response: Response):
        self.text = response.text
        self.sections = response.sections

    @override
    def guess_action(self) -> Tuple[ExperimentDescription | TestDescription | None, EquivalenceClaim | None]:
        claim = None
        equivalence_sections = [section for section in self.sections if section.kind == "equivalence"]
        if equivalence_sections:
            claim = EquivalenceClaim(text=equivalence_sections[0].text)

        for section in reversed(self.sections):
            if section.code_blocks:
                return TestDescription(text=section.text, code=section.code_blocks[-1]), claim

        return None, claim


class BaselineLoop(Loop):
    @override
    def _perform_next_step(self, state: State):
        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_action()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_for_action()
        elif state == State.TEST_STATED:
            self._run_test()
        elif state == State.TEST_DOESNT_COMPILE:
            self._prompt_for_action()
        elif state == State.TEST_DOESNT_DETECT_MUTANT:
            self._prompt_for_action()
        elif state == State.DONE:
            raise InvalidStateException(State.DONE)
        elif state == State.CLAIMED_EQUIVALENT:
            self._write_equivalence_message()
            # self._write_equivalence_result()
        elif state == State.EQUIVALENCE_MESSAGE_GIVEN:
            self._prompt_for_action()
        elif state == State.INCOMPLETE_RESPONSE:
            self._handle_incomplete_response()
        elif state == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
            self._prompt_for_action()
        elif state == State.ABORTED:
            raise InvalidStateException(State.ABORTED)
        elif state == State.INVALID:
            raise InvalidStateException(State.INVALID)
        elif state is None:
            raise InvalidStateException(None)
        else:
            raise InvalidStateException(None, "Invalid state for baseline.")

    @override
    def _init_conversation(self):
        """it's hard to do sometimes"""
        if self.prompts.system_prompt:
            self.add_msg(self.prompts.system_prompt.render(), tag=None)
            self.add_msg(self.prompts.baseline_prompt.render(self.problem), tag=None)
        self.add_msg(self.prompts.problem_template.render(self.problem, is_baseline=True), State.INITIAL)

    @override
    def _parse_response(self, text: str) -> Response:
        response = super()._parse_response(text)
        return BaselineReponse(response)

    @override
    def _complete(self) -> AssistantMessage:
        return self.endpoint.complete(self.conversation, stop=self.prompts.baseline_stop_words)

    @override
    def get_result(self) -> Result:
        result = super().get_result()
        result.implementation = "baseline"
        return result
