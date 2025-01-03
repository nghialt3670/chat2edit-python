import ast
import copy
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from chat2edit.base import ContextProvider, Llm, PromptStrategy
from chat2edit.constants import (
    MAX_CYCLES_PER_PROMPT_RANGE,
    MAX_LOOPS_PER_CYCLE_RANGE,
    MAX_PROMPTS_PER_LOOP_RANGE,
)
from chat2edit.context.manage import assign, safe_deepcopy
from chat2edit.context.utils import value_to_path
from chat2edit.execution.code import execute_code, process_code
from chat2edit.execution.exceptions import FeedbackException, ResponseException
from chat2edit.execution.feedbacks import (
    IncompleteCycleFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.execution.signaling import pop_feedback, pop_response
from chat2edit.models import ChatCycle, Error, Feedback, Message, PromptExecuteLoop
from chat2edit.prompting.strategies.otc_strategy import OtcStrategy


class Chat2EditConfig(BaseModel):
    max_cycles_per_prompt: int = Field(
        default=15,
        ge=MAX_CYCLES_PER_PROMPT_RANGE[0],
        le=MAX_CYCLES_PER_PROMPT_RANGE[1],
    )
    max_loops_per_cycle: int = Field(
        default=4,
        ge=MAX_LOOPS_PER_CYCLE_RANGE[0],
        le=MAX_LOOPS_PER_CYCLE_RANGE[1],
    )
    max_prompts_per_loop: int = Field(
        default=2,
        ge=MAX_PROMPTS_PER_LOOP_RANGE[0],
        le=MAX_PROMPTS_PER_LOOP_RANGE[1],
    )


class Chat2EditCallbacks(BaseModel):
    on_request: Optional[Callable[[Message], None]] = Field(default=None)
    on_prompt: Optional[Callable[[str], None]] = Field(default=None)
    on_answer: Optional[Callable[[str], None]] = Field(default=None)
    on_extract: Optional[Callable[[str], None]] = Field(default=None)
    on_process: Optional[Callable[[str], None]] = Field(default=None)
    on_execute: Optional[Callable[[str], None]] = Field(default=None)
    on_feedback: Optional[Callable[[Feedback], None]] = Field(default=None)
    on_respond: Optional[Callable[[Message], None]] = Field(default=None)


class Chat2Edit:
    def __init__(
        self,
        cycles: List[ChatCycle],
        *,
        llm: Llm,
        provider: ContextProvider,
        strategy: PromptStrategy = OtcStrategy(),
        config: Chat2EditConfig = Chat2EditConfig(),
        callbacks: Chat2EditCallbacks = Chat2EditCallbacks(),
    ) -> None:
        self.cycles = cycles
        self.llm = llm
        self.provider = provider
        self.strategy = strategy
        self.config = config
        self.callbacks = callbacks

    async def send(self, message: Message) -> Optional[Message]:
        cycle = ChatCycle(request=message)

        self.cycles.append(cycle)
        self._contextualize(cycle.request, cycle.context, existed=False)

        if self.callbacks.on_request:
            self.callbacks.on_request(cycle.request)

        cycle.context.update(safe_deepcopy(self.provider.get_context()))
        success_cycles = [cycle for cycle in self.cycles if cycle.response]

        if success_cycles:
            prev_context = success_cycles[-1].context

            if prev_context:
                cycle.context.update(safe_deepcopy(prev_context))

        curr_cycles = success_cycles[-self.config.max_cycles_per_prompt - 1 :]
        curr_cycles.append(cycle)

        while len(cycle.loops) < self.config.max_loops_per_cycle:
            loop = PromptExecuteLoop()
            cycle.loops.append(loop)

            loop.prompts, loop.answers, loop.error, code = await self._prompt(
                curr_cycles
            )

            if not code:
                break

            loop.blocks, loop.error, loop.feedback, response = await self._execute(
                code, cycle.context
            )

            if loop.feedback:
                self._contextualize(loop.feedback, cycle.context, existed=False)

            if response:
                cycle.response = copy.copy(response)

                self._contextualize(cycle.response, cycle.context, existed=True)

                if self.callbacks.on_respond:
                    self.callbacks.on_respond(cycle.response)

                return response

            if self.callbacks.on_feedback:
                self.callbacks.on_feedback(loop.feedback)

        return None

    def _contextualize(
        self, target: Union[Message, Feedback], context: Dict[str, Any], existed: bool
    ) -> None:
        target.attachments = (
            [value_to_path(att, context) for att in target.attachments]
            if existed
            else assign(target.attachments, context)
        )

    async def _prompt(
        self,
        cycles: List[ChatCycle],
    ) -> Tuple[List[str], List[str], Optional[Error], Optional[str]]:
        messages = []
        prompts = []
        answers = []
        error = None
        code = None

        exemplars = self.provider.get_exemplars()
        context = self.provider.get_context()

        while len(prompts) < self.config.max_prompts_per_loop:
            prompt = (
                self.strategy.get_refine_prompt()
                if prompts
                else self.strategy.create_prompt(cycles, exemplars, context)
            )

            prompts.append(prompt)
            messages.append(prompt)

            if self.callbacks.on_prompt:
                self.callbacks.on_prompt(prompt)

            try:
                answer = await self.llm.generate(messages)

                answers.append(answer)
                messages.append(answer)

                if self.callbacks.on_answer:
                    self.callbacks.on_answer

            except Exception as e:
                error = Error.from_exception(e)
                break

            try:
                code = self.strategy.extract_code(answer)

                if self.callbacks.on_extract:
                    self.callbacks.on_extract(code)

                break
            except:
                pass

        return prompts, answers, error, code

    async def _execute(
        self, code: str, context: Dict[str, Any]
    ) -> Tuple[List[str], Optional[Error], Optional[Feedback], Optional[Message]]:
        blocks = []
        error = None
        feedback = None
        response = None

        processed_code = process_code(code, context)

        if self.callbacks.on_process:
            self.callbacks.on_process(processed_code)

        try:
            tree = ast.parse(processed_code)
        except Exception as e:
            error = Error.from_exception(e)
            return blocks, error, feedback, response

        for node in tree.body:
            block = ast.unparse(node).strip()
            blocks.append(block)

            if self.callbacks.on_execute:
                self.callbacks.on_execute(block)

            try:
                await execute_code(block, context)

            except FeedbackException as e:
                feedback = e.feedback
                break

            except ResponseException as e:
                response = e.response
                break

            except Exception as e:
                error = Error.from_exception(e)
                feedback = UnexpectedErrorFeedback(error=error)
                break

            feedback = pop_feedback()
            response = pop_response()

            if feedback or response:
                break

        if not feedback and not response:
            feedback = IncompleteCycleFeedback()

        return blocks, error, feedback, response
