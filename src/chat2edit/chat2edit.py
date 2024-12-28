from copy import deepcopy
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

from chat2edit.base import ContextProvider, Llm, PromptStrategy
from chat2edit.constants import (
    MAX_CYCLES_PER_PROMPT_RANGE,
    MAX_LOOPS_PER_CYCLE_RANGE,
    MAX_PROMPTS_PER_LOOP_RANGE,
)
from chat2edit.context.manage import assign
from chat2edit.context.utils import value_to_path
from chat2edit.execution.execute import execute
from chat2edit.models import ChatCycle, Feedback, Message, PromptExecuteLoop
from chat2edit.prompting.prompt import prompt
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
    on_usr_request: Optional[Callable[[Message], None]] = Field(default=None)
    on_block_execute: Optional[Callable[[str], None]] = Field(default=None)
    on_sys_feedback: Optional[Callable[[Feedback], None]] = Field(default=None)
    on_llm_respond: Optional[Callable[[Message], None]] = Field(default=None)


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

        provided_context = self.provider.get_context()
        success_cycles = [cycle for cycle in self.cycles if cycle.response]

        if success_cycles and (prev_context := deepcopy(success_cycles[-1].context)):
            cycle.context.update(prev_context)
        else:
            cycle.context.update(deepcopy(provided_context))

        cycle.request.attachments = assign(cycle.request.attachments, cycle.context)

        if self.callbacks.on_usr_request:
            self.callbacks.on_usr_request(cycle.request)

        cycles = success_cycles[-self.config.max_cycles_per_prompt - 1 :]
        cycles.append(cycle)

        while len(cycle.loops) < self.config.max_loops_per_cycle:
            loop = PromptExecuteLoop()
            cycle.loops.append(loop)

            prompting_result = await prompt(
                cycles=cycles,
                llm=self.llm,
                provider=self.provider,
                strategy=self.strategy,
                max_prompts=self.config.max_prompts_per_loop,
            )

            loop.prompts = prompting_result.prompts
            loop.answers = prompting_result.answers
            loop.error = prompting_result.error

            if not prompting_result.code:
                break

            execution_result = await execute(
                code=prompting_result.code,
                context=cycle.context,
                on_block_execute=self.callbacks.on_block_execute,
            )

            loop.blocks = execution_result.blocks
            loop.feedback = execution_result.feedback
            loop.error = execution_result.error

            if loop.feedback:
                loop.feedback.attachments = [
                    value_to_path(att, cycle.context)
                    for att in loop.feedback.attachments
                ]

            if execution_result.response:
                cycle.response = Message(
                    text=execution_result.response.text,
                    attachments=[
                        value_to_path(att, cycle.context)
                        for att in execution_result.response.attachments
                    ],
                )

                if self.callbacks.on_llm_respond:
                    self.callbacks.on_llm_respond(cycle.response)

                return execution_result.response

            if self.callbacks.on_sys_feedback:
                self.callbacks.on_feedback(loop.feedback)

        return None
