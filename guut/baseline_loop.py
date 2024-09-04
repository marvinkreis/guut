from typing import override

from guut.llm import AssistantMessage
from guut.loop import InvalidStateException, Loop, RawExperiment, RawExperimentSection, State
from guut.parsing import extract_markdown_code_blocks


class BaselineLoop(Loop):
    @override
    def _perform_next_step(self, state: State):
        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_STATED:
            self._run_test()
        elif state == State.TEST_DOESNT_COMPILE:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_DOESNT_DETECT_MUTANT:
            self._prompt_for_hypothesis_or_test()
        elif state == State.DONE:
            raise InvalidStateException(State.DONE)
        elif state == State.INCOMPLETE_RESPONSE:
            self._handle_incomplete_response()
        elif state == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
            self._prompt_for_hypothesis_or_test()
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
    def _prompt_for_hypothesis_or_test(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.stop_words)
        response = self._clean_response(response)

        relevant_text = self._concat_incomplete_responses(include_message=response)
        raw_experiment = self._parse_experiment_description(relevant_text)
        experiment = raw_experiment.guess_experiment()

        if experiment is None:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)
            return
        else:
            self.add_msg(response, State.TEST_STATED)
            return

    @override
    def _parse_experiment_description(self, text: str) -> RawExperiment:
        code_blocks = extract_markdown_code_blocks(text)

        code_blocks_with_allowed_lang = [
            block.code
            for block in code_blocks
            if block.language is not None and block.language in self.problem.allowed_languages()
        ]
        if code_blocks_with_allowed_lang:
            return RawExperiment(
                text=text,
                sections=[
                    RawExperimentSection(
                        kind="test", text=text, code_blocks=code_blocks_with_allowed_lang, debugger_blocks=[]
                    )
                ],
            )

        code_blocks_without_lang = [block.code for block in code_blocks if block.language is None]
        if code_blocks_without_lang:
            return RawExperiment(
                text=text,
                sections=[
                    RawExperimentSection(
                        kind="test", text=text, code_blocks=code_blocks_without_lang, debugger_blocks=[]
                    )
                ],
            )

        return RawExperiment(
            text=text,
            sections=[RawExperimentSection(kind="none", text=text, code_blocks=[], debugger_blocks=[])],
        )

    @override
    def _generate_id(self) -> str:
        return f"baseline_{super()._generate_id()}"

    def _complete(self) -> AssistantMessage:
        return self.endpoint.complete(self.conversation, stop=self.prompts.baseline_stop_words)
