import ast
import inspect
import io
from contextlib import redirect_stdout
from copy import deepcopy
from itertools import zip_longest
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from IPython.core.interactiveshell import InteractiveShell
from pydantic import BaseModel, Field

from chat2edit.attachment import Attachment
from chat2edit.base import ContextProvider, Llm, PromptStrategy
from chat2edit.constants import (
    MAX_CYCLES_PER_PHASE_RANGE,
    MAX_PHASE_PER_PROMPT_RANGE,
    MAX_PROMPTS_PER_CYCLE_RANGE,
    MAX_VARNAME_SEARCH_INDEX,
)
from chat2edit.exceptions import FeedbackException
from chat2edit.feedbacks import (
    FunctionMessageFeedback,
    IncompleteCycleFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models import AssignedAttachment, Cycle, Error, Message, Phase
from chat2edit.signaling import (
    clear_feedback,
    clear_response,
    get_feedback,
    get_response,
)
from chat2edit.strategies import OtcStrategy
from chat2edit.utils.code import fix_unawaited_async_calls
from chat2edit.utils.context import path_to_obj
from chat2edit.utils.repr import create_obj_basename


class Chat2EditConfig(BaseModel):
    max_phase_per_prompt: int = Field(
        default=15,
        ge=MAX_PHASE_PER_PROMPT_RANGE[0],
        le=MAX_PHASE_PER_PROMPT_RANGE[1],
    )
    max_cycles_per_phase: int = Field(
        default=4,
        ge=MAX_CYCLES_PER_PHASE_RANGE[0],
        le=MAX_CYCLES_PER_PHASE_RANGE[1],
    )
    max_prompts_per_cycle: int = Field(
        default=2,
        ge=MAX_PROMPTS_PER_CYCLE_RANGE[0],
        le=MAX_PROMPTS_PER_CYCLE_RANGE[1],
    )


class Chat2Edit:
    def __init__(
        self,
        phases: List[Phase],
        *,
        llm: Llm,
        provider: ContextProvider,
        strategy: PromptStrategy = OtcStrategy(),
        config: Chat2EditConfig = Chat2EditConfig(),
    ):
        self._phases = phases
        self._llm = llm
        self._provider = provider
        self._strategy = strategy
        self._config = config

    def get_phases(self) -> List[Phase]:
        return self._phases

    def get_success_phases(self) -> List[Phase]:
        return list(filter(self._check_phase, self._phases))

    async def send(self, message: Message) -> Optional[Message]:
        phase = Phase()
        self._phases.append(phase)

        context = phase.context
        provided_context = self._provider.get_context()
        success_phases = self.get_success_phases()

        if success_phases and (prev_context := deepcopy(success_phases[-1].context)):
            context.update(prev_context)
        else:
            context.update(deepcopy(provided_context))

        shell = InteractiveShell.instance()
        context.update(shell.user_ns)
        shell.user_ns = context

        phases = success_phases[-self._config.max_phase_per_prompt - 1 :]
        phases.append(phase)

        attached_message = self._attach_message(message)
        trigger = self._assign_message(attached_message, context)

        while len(phase.cycles) < self._config.max_cycles_per_phase:
            cycle = Cycle(trigger=trigger)
            phase.cycles.append(cycle)

            # Prompting
            exemplars = self._provider.get_exemplars()
            prompt = self._strategy.create_prompt(phases, provided_context, exemplars)
            cycle.prompts.append(prompt)

            while len(cycle.prompts) < self._config.max_prompts_per_cycle:
                try:
                    prompt = cycle.prompts[-1]
                    messages = [
                        msg
                        for pair in zip_longest(cycle.prompts, cycle.answers)
                        for msg in pair
                        if msg is not None
                    ]
                    answer = await self._llm.generate(messages)
                    cycle.answers.append(answer)

                except Exception as e:
                    cycle.error = Error.from_exception(e)
                    break

                cycle.code = self._strategy.extract_code(cycle.answers[-1])

                if cycle.code:
                    break

                refine_prompt = self._strategy.get_refine_prompt()
                cycle.prompts.append(refine_prompt)

            if not cycle.code:
                break

            # Execution
            try:
                tree = ast.parse(cycle.code)
            except Exception as e:
                cycle.error = Error.from_exception(e)
                break

            async_func_names = [
                k for k, v in context.items() if inspect.iscoroutinefunction(v)
            ]

            for node in tree.body:
                block = ast.unparse(node)

                fixed_block = fix_unawaited_async_calls(block, async_func_names)
                cycle.blocks.append(fixed_block)

                try:
                    with io.StringIO() as buffer, redirect_stdout(buffer):
                        cell_result = await shell.run_cell_async(
                            fixed_block, silent=True
                        )
                        cell_result.raise_error()

                except FeedbackException as e:
                    cycle.result = e.feedback

                    if isinstance(cycle.result, FunctionMessageFeedback):
                        cycle.result.message = self._assign_message(
                            self._attach_message(cycle.result.message), context
                        )

                    break

                except Exception as e:
                    error = Error.from_exception(e)
                    cycle.result = UnexpectedErrorFeedback(error=error)
                    break

            if not cycle.result:
                cycle.result = (
                    get_response() or get_feedback() or IncompleteCycleFeedback()
                )

            clear_response()
            clear_feedback()

            if isinstance(cycle.result, Message):
                return self._create_message(cycle.result, context)

            trigger = cycle.result

        return None

    def _check_phase(self, phase: Phase) -> bool:
        return phase.cycles and isinstance(phase.cycles[-1].result, Message)

    def _attach_message(self, message: Message) -> Message:
        return Message(
            text=message.text,
            attachments=[self._provider.attach(att) for att in message.attachments],
        )

    def _assign_message(self, message: Message, context: Dict[str, Any]) -> Message:
        return Message(
            text=message.text,
            attachments=[
                self._assign_attachment(att, context) for att in message.attachments
            ],
        )

    def _create_message(self, message: Message, context: Dict[str, Any]) -> Message:
        return Message(
            text=message.text,
            attachments=[path_to_obj(att.path, context) for att in message.attachments],
        )

    def _assign_attachment(
        self,
        attachment: Attachment,
        context: Dict[str, Any],
        existing_varnames: Optional[Set[str]] = None,
    ) -> AssignedAttachment:
        if not existing_varnames:
            existing_varnames = set(context.keys())

        basename = attachment.__basename__ or create_obj_basename(attachment)
        varname = self._find_suitable_varname(basename, existing_varnames)

        existing_varnames.add(varname)
        context[varname] = attachment

        return AssignedAttachment(
            type=attachment.__class__.__name__,
            path=varname,
            attrpaths=attachment.__attrpaths__,
            attachments=[
                self._assign_attachment(att, context, existing_varnames)
                for att in attachment.__attachments__
            ],
        )

    def _find_suitable_varname(self, basename: str, existing_varnames: Set[str]) -> str:
        i = 0

        while i < MAX_VARNAME_SEARCH_INDEX:
            if (varname := f"{basename}_{i}") not in existing_varnames:
                return varname

            i += 1

        i = str(uuid4()).split("_").pop()
        return f"{basename}_{i}"
