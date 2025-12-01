from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from chat2edit.context.providers import CalculatorContextProvider, ContextProvider
from chat2edit.context.strategies import ContextStrategy, DefaultContextStrategy
from chat2edit.execution.feedbacks import IncompleteCycleFeedback
from chat2edit.execution.strategies import DefaultExecutionStrategy, ExecutionStrategy
from chat2edit.models import (
    ChatCycle,
    ChatMessage,
    ContextualizedFeedback,
    ExecutionBlock,
    ExecutionFeedback,
    LlmMessage,
    PromptCycle,
    PromptExchange,
)
from chat2edit.models.prompt_error import PromptError
from chat2edit.prompting.llms import GoogleLlm, Llm
from chat2edit.prompting.strategies import OtcPromptingStrategy, PromptingStrategy


class Chat2EditConfig(BaseModel):
    max_prompt_cycles: int = Field(default=4, ge=0)
    max_llm_exchanges: int = Field(default=2, ge=0)


class Chat2EditCallbacks(BaseModel):
    on_request: Optional[Callable[[ContextualizedFeedback], None]] = Field(default=None)
    on_prompt: Optional[Callable[[LlmMessage], None]] = Field(default=None)
    on_answers: Optional[Callable[[List[LlmMessage]], None]] = Field(default=None)
    on_extract: Optional[Callable[[str], None]] = Field(default=None)
    on_blocks: Optional[Callable[List[ExecutionBlock], None]] = Field(default=None)
    on_execute: Optional[Callable[[ExecutionBlock], None]] = Field(default=None)


class Chat2Edit:
    def __init__(
        self,
        *,
        llm: Llm = GoogleLlm("gemini-2.5-flash"),
        context_provider: ContextProvider = CalculatorContextProvider(),
        context_strategy: ContextStrategy = DefaultContextStrategy(),
        prompting_strategy: PromptingStrategy = OtcPromptingStrategy(),
        execution_strategy: ExecutionStrategy = DefaultExecutionStrategy(),
        callbacks: Chat2EditCallbacks = Chat2EditCallbacks(),
        config: Chat2EditConfig = Chat2EditConfig(),
    ) -> None:
        self._llm = llm
        self._context_provider = context_provider
        self._context_strategy = context_strategy
        self._prompting_strategy = prompting_strategy
        self._execution_strategy = execution_strategy
        self._callbacks = callbacks
        self._config = config

    async def generate(
        self,
        request: ChatMessage,
        cycles: Optional[List[ChatCycle]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[ChatMessage], ChatCycle, Dict[str, Any]]:
        # Avoid sharing mutable default arguments across invocations by creating fresh copies
        cycles = list(cycles) if cycles is not None else []
        context = dict(context) if context is not None else {}

        context.update(self._context_provider.get_context())
        contextualized_request = self._context_strategy.contextualize_message(
            request, context
        )
        chat_cycle = ChatCycle(request=contextualized_request)
        cycles.append(chat_cycle)

        if self._callbacks.on_request:
            self._callbacks.on_request(chat_cycle.request)

        while len(chat_cycle.cycles) < self._config.max_prompt_cycles:
            prompt_cycle = PromptCycle()
            chat_cycle.cycles.append(prompt_cycle)
            prompt_cycle.exchanges = await self._prompt(cycles)

            if not prompt_cycle.exchanges or not prompt_cycle.exchanges[-1].code:
                break

            code = prompt_cycle.exchanges[-1].code
            prompt_cycle.blocks = await self._execute(code, context)

            executed_blocks = list(filter(lambda block: block.is_executed, prompt_cycle.blocks))
            if executed_blocks and (
                executed_blocks[-1].response or executed_blocks[-1].error
            ):
                break

        return (
            self._get_response(chat_cycle, context),
            chat_cycle,
            self._context_strategy.filter_context(context),
        )

    async def _prompt(
        self,
        cycles: List[ChatCycle],
    ) -> PromptCycle:
        exemplars = self._context_provider.get_exemplars()
        context = self._context_provider.get_context()
        exchanges = []

        while len(exchanges) < self._config.max_llm_exchanges:
            prompt = (
                self._prompting_strategy.get_refine_prompt()
                if exchanges
                else self._prompting_strategy.create_prompt(cycles, exemplars, context)
            )
            exchange = PromptExchange(prompt=prompt)
            exchanges.append(exchange)

            if self._callbacks.on_prompt:
                self._callbacks.on_prompt(exchange.prompt)

            try:
                history = [[e.prompt, e.answers[0]] for e in exchanges[:-1]]
                exchange.answers = await self._llm.generate(exchange.prompt, history)

                if self._callbacks.on_answers:
                    self._callbacks.on_answers(exchange.answers)

            except Exception as e:
                error = PromptError.from_exception(e)
                error.llm = self._llm.get_info()
                exchange.error = error
                break

            answer = exchange.answers[0]
            exchange.code = self._prompting_strategy.extract_code(answer.text)

            if exchange.code:
                if self._callbacks.on_extract:
                    self._callbacks.on_extract(exchange.code)

                break

        return exchanges

    async def _execute(self, code: str, context: Dict[str, Any]) -> List[str]:
        generated_code_blocks = self._execution_strategy.parse(code)
        processed_code_blocks = [
            self._execution_strategy.process(block, context)
            for block in generated_code_blocks
        ]
        blocks = [
            ExecutionBlock(generated_code=generated_code, processed_code=processed_code)
            for generated_code, processed_code in zip(
                generated_code_blocks, processed_code_blocks
            )
        ]

        if self._callbacks.on_blocks:
            self._callbacks.on_blocks(blocks)

        for block in blocks:
            feedback, response, error, logs = await self._execution_strategy.execute(
                block.processed_code, context
            )
            block.is_executed = True
            block.feedback = (
                None
                if not feedback
                else (
                    self._context_strategy.contextualize_feedback(feedback, context)
                    if isinstance(feedback, ExecutionFeedback)
                    else feedback
                )
            )
            block.response = (
                self._context_strategy.contextualize_message(response, context)
                if response
                else None
            )
            block.error = error
            block.logs = logs

            if self._callbacks.on_execute:
                self._callbacks.on_execute(block)

            if feedback or response or error:
                break

        executed_blocks = list(filter(lambda block: block.is_executed, blocks))
        last_executed_block = executed_blocks[-1]
        if not (
            last_executed_block.feedback
            or last_executed_block.response
            or last_executed_block.error
        ):
            last_executed_block.feedback = IncompleteCycleFeedback()

        return blocks

    def _get_response(
        self, chat_cycle: ChatCycle, context: Dict[str, Any]
    ) -> Optional[ChatMessage]:
        if not chat_cycle.cycles:
            return None

        last_prompt_cycle = chat_cycle.cycles[-1]
        if not last_prompt_cycle.blocks:
            return None

        executed_blocks = list(
            filter(lambda block: block.is_executed, last_prompt_cycle.blocks)
        )
        if not executed_blocks:
            return None

        last_executed_block = executed_blocks[-1]
        if not last_executed_block.response:
            return None

        return self._context_strategy.decontextualize_message(
            last_executed_block.response, context
        )
