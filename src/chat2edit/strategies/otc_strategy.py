from itertools import chain
from typing import Any, Dict, Iterable, List, Optional, Tuple

from chat2edit.base import PromptStrategy
from chat2edit.constants import CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY
from chat2edit.feedbacks import (
    Feedback,
    FileObjModifiedFeedback,
    FunctionMessageFeedback,
    IncompleteCycleFeedback,
    InvalidArgumentFeedback,
    UnassignedValueFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models import Cycle, Message, Phase
from chat2edit.stubbing.stubs import CodeStub

OTC_PROMPT_TEMPLATE = """Given this context code:

{context_code}

Follow these exemplary observation-thinking-commands sequences:

{exemplary_otc_sequences}

Give the next thinking and commands for the current sequence:
Note: Answer in plain text

{current_otc_sequences}"""

OTC_SEQUENCE_TEMPLATE = (
    "observation: {observation}\nthinking: {thinking}\ncommands:\n{commands}"
)

OTC_REFINE_PROMPT = """Please answer in this format:

thinking: <YOUR_THINKING>
commands:
<YOUR_COMMANDS>"""

INVALID_ARGUMENT_FEEDBACK_TEXT_TEMPLATE = "In function `{func_name}`, argument for `{param_name}` must be of type `{param_anno}`, but received type `{param_type}`"
FILE_OBJ_MODIFIED_FEEDBACK_TEXT_TEMPLATE = "The variable `{varname}` holds a file object, which cannot be modified directly. To make changes, create a copy of the object using `deepcopy` and modify the copy instead."
UNASSIGNED_VALUE_FEEDBACK_TEXT_TEMPLATE = "The function `{func_name}` returns a value of type `{ret_anno}`, but it is not utilized in the code."
FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = (
    "Unexpected error occurred in function `{func_name}`"
)
UNEXPECTED_ERROR_FEEDBACK_TEXT = "Unexpected error occurred."
INCOMPLETE_CYCLE_FEEDBACK_TEXT = "The commands executed successfully. Please continue."


class OtcStrategy(PromptStrategy):
    def create_prompt(
        self, phases: List[Phase], context: Dict[str, Any], exemplars: List[Phase]
    ) -> str:
        return OTC_PROMPT_TEMPLATE.format(
            context_code=str(CodeStub.from_context(context=context)),
            exemplary_otc_sequences="\n\n".join(
                (
                    f"Exemplar {idx + 1}:\n"
                    + "\n".join(map(self._create_otc_sequence, exemplar.cycles))
                )
                for idx, exemplar in enumerate(exemplars)
            ),
            current_otc_sequences="\n".join(
                map(
                    self._create_otc_sequence,
                    chain.from_iterable(phase.cycles for phase in phases),
                )
            ),
        )

    def get_refine_prompt(self) -> str:
        return OTC_REFINE_PROMPT

    def extract_code(self, text: str) -> Optional[str]:
        _, code = self._extract_thinking_commands(text)
        return code

    def _create_otc_sequence(self, cycle: Cycle) -> str:
        return OTC_SEQUENCE_TEMPLATE.format(
            observation=(
                self._create_observation_from_message(cycle.trigger)
                if cycle.is_request()
                else self._create_observation_from_feedback(cycle.trigger)
            ),
            thinking=(
                self._extract_thinking_commands(cycle.answers[-1])[0]
                if cycle.answers
                else "..."
            ),
            commands="\n".join(cycle.blocks) if cycle.blocks else "...",
        ).strip()

    def _create_observation_from_message(self, message: Message) -> str:
        if not message.attachments:
            return f'user_message("{message.text}")'

        chained_paths = chain.from_iterable(
            att.get_all_paths() for att in message.attachments
        )

        paths_repr = ", ".join(list(chained_paths))
        return f'user_message("{message.text}", variables=[{paths_repr}])'

    def _create_observation_from_feedback(self, feedback: Feedback) -> str:
        text: str = ""
        paths: Optional[Iterable[str]] = None

        if isinstance(feedback, InvalidArgumentFeedback):
            text = INVALID_ARGUMENT_FEEDBACK_TEXT_TEMPLATE.format(
                func_name=feedback.func,
                param_name=feedback.param.name,
                param_anno=feedback.param.anno,
                param_type=feedback.param.type,
            )

        elif isinstance(feedback, FunctionMessageFeedback):
            message = feedback.message
            text = message.text

            if message.attachments:
                paths = chain.from_iterable(
                    att.get_all_paths() for att in message.attachments
                )

        elif isinstance(feedback, FileObjModifiedFeedback):
            text = FILE_OBJ_MODIFIED_FEEDBACK_TEXT_TEMPLATE.format(
                varname=feedback.varname
            )

        elif isinstance(feedback, UnassignedValueFeedback):
            text = UNASSIGNED_VALUE_FEEDBACK_TEXT_TEMPLATE.format(
                func_name=feedback.func, ret_anno=feedback.anno
            )

        elif isinstance(feedback, UnexpectedErrorFeedback):
            if feedback.func:
                text = FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE.format(
                    func_name=feedback.func
                )
            else:
                text = UNEXPECTED_ERROR_FEEDBACK_TEXT

        elif isinstance(feedback, IncompleteCycleFeedback):
            text = INCOMPLETE_CYCLE_FEEDBACK_TEXT

        else:
            raise ValueError(f"Unknown feedback: {feedback}")

        if not paths:
            return f'system_{feedback.severity}("{text}")'

        return f'system_{feedback.severity}("{text}", variables=[{", ".join(paths)}])'

    def _extract_thinking_commands(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = [
            part.strip()
            for part in text.replace("observation:", "$")
            .replace("thinking:", "$")
            .replace("commands:", "$")
            .split("$")
            if part.strip()
        ]

        thinking = parts[-2] if len(parts) >= 2 else None
        commands = parts[-1] if len(parts) >= 2 else None

        return thinking, commands
