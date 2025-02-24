from typing import override

from guut.llm import AssistantMessage
from guut.loop import (
    Action,
    ActionKind,
    InvalidStateException,
    Loop,
    LoopSettings,
    ParsedResponse,
    State,
)


class BaselineSettings(LoopSettings):
    @override
    def __init__(
        self,
        preset_name: str = "baseline_generic",
        max_num_experiments: int = 0,
        max_num_tests: int = 99,
        max_num_incomplete_responses: int = 2,
        max_num_turns: int = 10,
        test_inctructions_after_turn: int = 99,
        is_baseline=True,
    ):
        super().__init__(
            preset_name=preset_name,
            max_num_experiments=0,
            max_num_tests=max_num_tests,
            max_num_incomplete_responses=max_num_incomplete_responses,
            max_num_turns=max_num_turns,
            test_inctructions_after_turn=test_inctructions_after_turn,
            include_example=False,
            is_baseline=True,
        )


class BaselineParsedReponse(ParsedResponse):
    def __init__(self, response: ParsedResponse):
        self.text = response.text
        self.sections = response.sections

    @override
    def guess_action(self) -> Action | None:
        claim = None
        equivalence_sections = [section for section in self.sections if section.kind == ActionKind.EQUIVALENCE]
        if equivalence_sections:
            claim = Action(kind=ActionKind.EQUIVALENCE, text=equivalence_sections[0].text, claims_equivalent=True)

        for section in reversed(self.sections):
            if section.code_blocks:
                return Action(
                    kind=ActionKind.TEST,
                    text=section.text,
                    code=section.code_blocks[-1],
                    claims_equivalent=(claim is not None),
                )

        return claim


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
            if self.settings.max_num_tests == 1:
                self.add_msg(self.prompts.baseline_without_iterations_prompt.render(self.problem), tag=None)
            else:
                self.add_msg(self.prompts.baseline_prompt.render(self.problem), tag=None)
        self.add_msg(self.prompts.problem_template.render(self.problem, is_baseline=True), State.INITIAL)

    @override
    def _parse_response(self, text: str) -> ParsedResponse:
        response = super()._parse_response(text)
        return BaselineParsedReponse(response)

    @override
    def _complete(self) -> AssistantMessage:
        return self.endpoint.complete(self.conversation, stop=self.prompts.baseline_stop_words)
