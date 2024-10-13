import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple, Type

from llm import LLMEndpoint
from loguru import logger
from loop import Loop, LoopSettings, Result, Test

from guut.cosmic_ray import CosmicRayProblem, KilledMutant, MultipleMutantsResult, MutantSpec
from guut.logging import ConversationLogger, MessagePrinter
from guut.problem import Coverage, Problem


@dataclass
class ResultWithKilledMutants(Result):
    killed_mutants: List[KilledMutant]

    @staticmethod
    def create(result: Result, killed_mutants: List[KilledMutant]):
        return ResultWithKilledMutants(
            tests=result.tests,
            experiments=result.experiments,
            conversation=result.conversation,
            mutant_killed=result.mutant_killed,
            claimed_equivalent=result.claimed_equivalent,
            timestamp=result.timestamp,
            endpoint=result.endpoint,
            problem=result.problem,
            settings=result.settings,
            id=result.id,
            long_id=result.long_id,
            aborted=result.aborted,
            abort_reason=result.abort_reason,
            killed_mutants=killed_mutants,
        )


class CosmicRayRunner:
    def __init__(
        self,
        mutant_specs: List[MutantSpec],
        module_path: Path,
        python_interpreter: Path,
        endpoint: LLMEndpoint,
        loop_cls: Type[Loop],
        conversation_logger: ConversationLogger | None,
        message_printer: MessagePrinter | None,
        loop_settings: LoopSettings,
    ):
        self.mutants = mutant_specs[::]
        self.alive_mutants = mutant_specs[::]
        self.mutant_queue = mutant_specs[::]
        self.killed_mutants: List[KilledMutant] = []
        self.module_path = module_path
        self.python_interpreter = python_interpreter
        self.endpoint = endpoint
        self.loop_cls = loop_cls
        self.conversation_logger = conversation_logger
        self.message_printer = message_printer
        self.loop_settings = loop_settings
        self.tests: List[Tuple[str, Test]] = []

    def next_mutant(self) -> MutantSpec:
        mutant = random.choice(self.mutant_queue)
        self.mutant_queue.remove(mutant)
        return mutant

    def run_against_alive_mutants(self, test: Test) -> List[KilledMutant]:
        assert test.result is not None and test.result.correct is not None

        coverage = test.result.correct.coverage
        if coverage is None:
            raise Exception("No coverage was generated for the test.")
        if coverage.raw is None:
            raise Exception("Full coverage missing for the test.")
        # TODO: fall back to no coverage optimization if there is no coverage?

        killed_mutants = []
        for mutant in self.alive_mutants[::]:
            if self.is_mutant_covered(mutant, coverage):
                problem = CosmicRayProblem(
                    module_path=self.module_path,
                    target_path=mutant.target_path,
                    mutant_op_name=mutant.mutant_op,
                    occurrence=mutant.occurrence,
                    python_interpreter=self.python_interpreter,
                )
                logger.debug(f"Running test against mutant: {mutant}")
                exec_result = problem.run_test(code=test.code, collect_coverage=True)
                if exec_result.correct.exitcode == 0 and exec_result.mutant.exitcode != 0:
                    logger.info(f"Test killed mutant: {mutant}")
                    if mutant in self.alive_mutants:
                        self.alive_mutants.remove(mutant)
                    if mutant in self.mutant_queue:
                        self.mutant_queue.remove(mutant)
                    m = KilledMutant(mutant, test_result=exec_result)
                    killed_mutants.append(m)
                    self.killed_mutants.append(m)

        return killed_mutants

    def is_mutant_covered(self, mutant: MutantSpec, coverage: Coverage) -> bool:
        assert coverage.raw
        files = coverage.raw["files"]
        if file_coverage := files.get(f"{self.module_path.name}/{mutant.target_path}"):
            return any(
                [line in file_coverage["executed_lines"] for line in range(mutant.line_start, mutant.line_end + 1)]
            )
        else:
            return False

    def generate_tests(self, problem_cb: Callable[[Problem], None]):
        while self.mutant_queue:
            mutant = self.next_mutant()
            problem = CosmicRayProblem(
                module_path=self.module_path,
                target_path=mutant.target_path,
                mutant_op_name=mutant.mutant_op,
                occurrence=mutant.occurrence,
                python_interpreter=self.python_interpreter,
            )
            problem.validate_self()
            problem_cb(problem)

            # TODO: solve this better
            prompts = problem.get_default_prompts()

            loop = self.loop_cls(
                problem=problem,
                endpoint=self.endpoint,
                prompts=prompts,
                printer=self.message_printer,
                logger=self.conversation_logger,
                settings=self.loop_settings,
            )

            logger.info(f"Starting loop for {mutant}")
            result = loop.iterate()
            killed_mutants = []
            if test := result.get_killing_test():
                logger.info(f"Loop killed the assigned mutant {mutant}")
                if mutant in self.alive_mutants:
                    self.alive_mutants.remove(mutant)
                m = KilledMutant(mutant, test.result)
                killed_mutants.append(m)
                self.killed_mutants.append(m)
                killed_mutants += self.run_against_alive_mutants(test)
                logger.info(f"Test killed {len(killed_mutants) - 1} additional mutants.")
                logger.info(f"Remaining mutants: {len(self.alive_mutants)}")
                self.tests.append((result.long_id, test))
            else:
                logger.info("Loop failed to create a killing test.")

            result = ResultWithKilledMutants.create(result, killed_mutants)
            yield result

    def get_result(self):
        return MultipleMutantsResult(
            mutants=self.mutants, alive_mutants=self.alive_mutants, killed_mutants=self.killed_mutants, tests=self.tests
        )
