from typing import List, Optional

from pydantic import BaseModel, Field

from chat2edit.base import ContextProvider, Llm, PromptStrategy
from chat2edit.constants import (
    NUM_CHAT_CYCLES_PER_PROMPT_RANGE,
    NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE,
    NUM_PROMPTS_PER_EDIT_CYCLE_RANGE,
)
from chat2edit.context import (
    assign_message,
    contextualize_message,
    create_message,
    decontextualize_message,
    retrieve_message,
)
from chat2edit.execute import execute
from chat2edit.models import ChatCycle, EditCycle, Message
from chat2edit.prompt import prompt
from chat2edit.strategies import OtcStrategy


class Chat2EditConfig(BaseModel):
    max_ec_per_cc: int = Field(
        default=4,
        ge=NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE[0],
        le=NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE[1],
    )
    max_cc_per_p: int = Field(
        default=15,
        ge=NUM_CHAT_CYCLES_PER_PROMPT_RANGE[0],
        le=NUM_CHAT_CYCLES_PER_PROMPT_RANGE[1],
    )
    max_p_per_ec: int = Field(
        default=2,
        ge=NUM_PROMPTS_PER_EDIT_CYCLE_RANGE[0],
        le=NUM_PROMPTS_PER_EDIT_CYCLE_RANGE[1],
    )


class Chat2Edit:
    def __init__(
        self,
        *,
        provider: ContextProvider,
        llm: Llm,
        strategy: PromptStrategy = OtcStrategy(),
        config: Chat2EditConfig = Chat2EditConfig(),
        history: List[ChatCycle] = [],
    ):
        self._provider = provider
        self._strategy = strategy
        self._llm = llm
        self._config = config
        self._history = history

    def set_history(self, history: List[ChatCycle]) -> None:
        self._history = history

    def get_history(self) -> List[ChatCycle]:
        return self._history

    def clear_hisotry(self) -> None:
        self._history = []

    def pop_history(self) -> None:
        self._history.pop()

    async def send(self, message: Message) -> Optional[Message]:
        context = self._provider.get_context()

        request = assign_message(message, context.exec_context)
        chat_cycle = ChatCycle(
            request=request,
            context=context,
        )

        self._history.append(chat_cycle)

        completed_cycles = [c for c in self._history if c.is_completed()]
        main_cycles = completed_cycles[-self._config.max_cc_per_p :] + [chat_cycle]

        while len(chat_cycle.edit_cycles) < self._config.max_ec_per_cc:
            prompting_result = await prompt(
                cycles=main_cycles,
                llm=self._llm,
                strategy=self._strategy,
                context=self._provider.get_context(),
                max_prompts=self._config.max_p_per_pc,
            )

            edit_cycle = EditCycle(prompting_result=prompting_result)
            chat_cycle.edit_cycles.append(edit_cycle)

            if not prompting_result.code:
                break

            execution_result = await execute(
                code=prompting_result.code,
                exec_context=chat_cycle.context.exec_context,
                provider=self._provider,
            )

            edit_cycle.execution_result = execution_result

            if execution_result.error:
                break

            if execution_result.response:
                message = execution_result.response
                return create_message(message, chat_cycle.context.exec_context)

        return None
