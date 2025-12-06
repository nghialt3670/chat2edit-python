from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from chat2edit.context.providers import CalculatorContextProvider, ContextProvider
from chat2edit.context.strategies import ContextStrategy, DefaultContextStrategy
from chat2edit.execution.feedbacks import IncompleteCycleFeedback
from chat2edit.execution.strategies import DefaultExecutionStrategy, ExecutionStrategy
from chat2edit.models import (
    ChatCycle,
    ExecutionBlock,
    Exemplar,
    Feedback,
    Message,
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
    on_request: Optional[Callable[[Message], None]] = Field(default=None)
    on_prompt: Optional[Callable[[Message], None]] = Field(default=None)
    on_answer: Optional[Callable[[Message], None]] = Field(default=None)
    on_extract: Optional[Callable[[str], None]] = Field(default=None)
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
        self._exemplars = self._context_strategy.contextualize_exemplar(
            self._context_provider.get_exemplars(), {}
        )

    async def generate(
        self,
        request: Message,
        cycles: Optional[List[ChatCycle]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Message], ChatCycle, Dict[str, Any]]:
        # Avoid sharing mutable default arguments across invocations by creating fresh copies
        cycles = list(cycles) if cycles is not None else []
        context = dict(context) if context is not None else {}

        context.update(self._context_provider.get_context())
        contextualized_request = self._context_strategy.contextualize_message(request, context)
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

            executed_blocks = list(filter(lambda block: block.executed, prompt_cycle.blocks))
            if executed_blocks and (executed_blocks[-1].response or executed_blocks[-1].error):
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
        context = self._context_provider.get_context()
        exchanges = []

        while len(exchanges) < self._config.max_llm_exchanges:
            prompt = (
                self._prompting_strategy.get_refine_prompt()
                if exchanges
                else self._prompting_strategy.create_prompt(cycles, self._exemplars, context)
            )
            exchange = PromptExchange(prompt=prompt)
            exchanges.append(exchange)

            if self._callbacks.on_prompt:
                self._callbacks.on_prompt(exchange.prompt)

            try:
                history = [[e.prompt, e.answer] for e in exchanges[:-1]]
                exchange.answer = await self._llm.generate(exchange.prompt, history)

                if self._callbacks.on_answer:
                    self._callbacks.on_answer(exchange.answer)

            except Exception as e:
                error = PromptError.from_exception(e)
                error.llm = self._llm.get_info()
                exchange.error = error
                break

            exchange.code = self._prompting_strategy.extract_code(exchange.answer.text)

            if exchange.code:
                if self._callbacks.on_extract:
                    self._callbacks.on_extract(exchange.code)

                break

        return exchanges

    async def _execute(self, code: str, context: Dict[str, Any]) -> List[str]:
        generated_code_blocks = self._execution_strategy.parse(code)
        processed_code_blocks = [
            self._execution_strategy.process(block, context) for block in generated_code_blocks
        ]
        blocks = [
            ExecutionBlock(generated_code=generated_code, processed_code=processed_code)
            for generated_code, processed_code in zip(generated_code_blocks, processed_code_blocks)
        ]

        for block in blocks:
            feedback, response, error, logs = await self._execution_strategy.execute(
                block.processed_code, context
            )
            block.executed = True
            block.feedback = (
                None
                if not feedback
                else (
                    self._context_strategy.contextualize_feedback(feedback, context)
                    if isinstance(feedback, Feedback)
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

        executed_blocks = list(filter(lambda block: block.executed, blocks))
        last_executed_block = executed_blocks[-1]
        if not (
            last_executed_block.feedback
            or last_executed_block.response
            or last_executed_block.error
        ):
            last_executed_block.feedback = IncompleteCycleFeedback()

        return blocks

    def _get_response(self, chat_cycle: ChatCycle, context: Dict[str, Any]) -> Optional[Message]:
        if not chat_cycle.cycles:
            return None

        last_prompt_cycle = chat_cycle.cycles[-1]
        if not last_prompt_cycle.blocks:
            return None

        executed_blocks = list(filter(lambda block: block.executed, last_prompt_cycle.blocks))
        if not executed_blocks:
            return None

        last_executed_block = executed_blocks[-1]
        if not last_executed_block.response:
            return None

        return self._context_strategy.decontextualize_message(last_executed_block.response, context)

    def _contextualize_exemplar(self, exemplar: Exemplar) -> Exemplar:
        context = self._context_provider.get_context()

        for chat_cycle in exemplar.cycles:
            if not chat_cycle.request.contextualized:
                chat_cycle.request = self._context_strategy.contextualize_message(
                    chat_cycle.request, context
                )
                chat_cycle.request.contextualized = True
            for prompt_cycle in chat_cycle.cycles:
                for exchange in prompt_cycle.exchanges:
                    if not exchange.answer.contextualized:
                        exchange.answer = self._context_strategy.contextualize_message(
                            exchange.answer, context
                        )
                        exchange.answer.contextualized = True
                for block in prompt_cycle.blocks:
                    if block.feedback and not block.feedback.contextualized:
                        block.feedback = self._context_strategy.contextualize_feedback(
                            block.feedback, context
                        )
                        block.feedback.contextualized = True
                    if block.response and not block.response.contextualized:
                        block.response = self._context_strategy.contextualize_message(
                            block.response, context
                        )
                        block.response.contextualized = True

        return exemplar
