import inspect
from typing import Any, Dict, List, Optional, Tuple

from chat2edit.base import PromptStrategy
from chat2edit.constants import CLASS_OR_FUNCTION_STUB_KEY, MODULE_NAME
from chat2edit.models.context import Context
from chat2edit.models.cycles import ChatCycle
from chat2edit.models.execution import (
    ExecutionFeedback,
    FileObjModifiedFeedback,
    FunctionMessageFeedback,
    IncompleteCycleFeedback,
    InvalidArgumentFeedback,
    UnassignedValueFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models.messages import ContextMessage

OTC_PROMPT_TEMPLATE = """
Given the execution context:

{exec_context_repr}

Follow these observation-thinking-commands exemplary sequences:

{exem_otc_sequences}

Give the next thinking and commands for the current sequence:
Note: Answer in plain text

{main_otc_sequences}
"""

OTC_SEQUENCE_TEMPLATE = """observation: {observation}
thinking: {thinking}
commands:
{commands}
"""

OTC_REFINE_PROMPT = """
Please answer in this format:

thinking: <YOUR_THINKING>
commands:
<YOUR_COMMANDS>
"""

INVALID_ARGUMENT_FEEDBACK_TEXT_TEMPLATE = "In function `{func_name}`, argument for `{param_name}` must be of type `{param_anno}`, but received type `{param_type}`"
FILE_OBJ_MODIFIED_FEEDBACK_TEXT_TEMPLATE = "The variable `{varname}` holds a file object, which cannot be modified directly. To make changes, create a copy of the object using `deepcopy` and modify the copy instead."
UNASSIGNED_VALUE_FEEDBACK_TEXT_TEMPLATE = "The function `{func_name}` returns a value of type `{ret_anno}`, but it is not utilized in the code."
INCOMPLETE_CYCLE_FEEDBACK_TEXT = "The commands executed successfully. Please continue."
UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = (
    "Unexpected error occurred in function `{func_name}`"
)


class OtcStrategy(PromptStrategy):
    def create_prompt(self, chat_cycles: List[ChatCycle], context: Context) -> str:
        exec_context_repr = self._create_exec_context_repr(context.exec_context)
        exem_otc_sequences = self._create_exem_otc_sequences_repr(context.exem_cycles)
        main_otc_sequences = self._create_main_otc_sequences_repr(chat_cycles)

        return OTC_PROMPT_TEMPLATE.format(
            exec_context_repr=exec_context_repr,
            exem_otc_sequences=exem_otc_sequences,
            main_otc_sequences=main_otc_sequences,
        ).strip()

    def get_refine_prompt(self) -> str:
        return OTC_REFINE_PROMPT

    def extract_code(self, text: str) -> Optional[str]:
        _, code = self._extract_thinking_commands(text)
        return code

    def _create_exec_context_repr(self, context: Dict[str, Any]) -> str:
        import_statements = []
        class_stubs = []
        func_stubs = []

        for k, v in context.items():
            module = inspect.getmodule(v)

            if not module:
                continue

            module_name = module.__name__
            qual_name = getattr(v, "__qualname__", v.__name__)

            if module_name.startswith(MODULE_NAME):
                stub = getattr(v, CLASS_OR_FUNCTION_STUB_KEY, None)

                if not stub:
                    continue

                if inspect.isclass(v):
                    class_stubs.append(stub)
                elif inspect.isfunction:
                    func_stubs.append(stub)
            else:
                statement = None

                if qual_name != module_name:
                    statement = f"from {module_name} import {qual_name}"
                else:
                    statement = f"import {module_name}"

                if k != qual_name:
                    statement += f" as {k}"

                import_statements.append(statement)

        exec_context_repr_parts = []

        if import_statements:
            exec_context_repr_parts.append("\n".join(import_statements))

        if class_stubs:
            exec_context_repr_parts.append("\n\n".join(class_stubs))

        if func_stubs:
            exec_context_repr_parts.append("\n".join(func_stubs))

        return "\n\n".join(exec_context_repr_parts)

    def _create_exem_otc_sequences_repr(self, exemplars: List[ChatCycle]) -> str:
        return "".join(
            f"Exemplar {idx + 1}:\n{self._create_otc_sequence(exemplar)}"
            for idx, exemplar in enumerate(exemplars)
        )

    def _create_main_otc_sequences_repr(self, chat_cycles: List[ChatCycle]) -> str:
        return "".join(self._create_otc_sequence(cycle) for cycle in chat_cycles)

    def _create_otc_sequence(self, chat_cycle: ChatCycle) -> str:
        request_obs = self._create_obs_from_request(chat_cycle.request)
        steps = [request_obs]

        for prompt_cycle in chat_cycle.prompt_cycles:
            if (
                prompt_cycle.prompting_result.error
                or prompt_cycle.execution_result.error
            ):
                continue

            answer = prompt_cycle.prompting_result.messages[-1]
            thinking, _ = self._extract_thinking_commands(answer)
            executed_blocks = prompt_cycle.execution_result.blocks
            executed_cmds = self._create_commmands_str(executed_blocks)

            steps.append(thinking)
            steps.append(executed_cmds)

            feedback = prompt_cycle.execution_result.feedback

            if not feedback:
                continue

            feedback_obs = self._create_obs_from_feedback(feedback)
            steps.append(feedback_obs)

        steps += [""] * 2

        template_values_list = [
            {
                "observation": steps[i],
                "thinking": steps[i + 1],
                "commands": steps[i + 2],
            }
            for i in range(0, len(steps) - 2, 3)
        ]

        return "".join(
            OTC_SEQUENCE_TEMPLATE.format(**values) for values in template_values_list
        )

    def _create_obs_from_request(self, message: ContextMessage) -> str:
        if not message.objs_or_paths:
            return f'user_message("{message.text}")'

        var_names_repr = ", ".join(message.objs_or_paths)

        return f'user_message("{message.text}", variables=[{var_names_repr}])'

    def _create_obs_from_feedback(self, feedback: ExecutionFeedback) -> str:
        obs = f"system_{feedback.severity}"

        if isinstance(feedback, InvalidArgumentFeedback):
            text = INVALID_ARGUMENT_FEEDBACK_TEXT_TEMPLATE.format(
                func_name=feedback.func_name,
                param_name=feedback.param_name,
                param_anno=feedback.param_anno,
                param_type=feedback.param_type,
            )
            return obs + f'("{text}")'

        if isinstance(feedback, FunctionMessageFeedback):
            if feedback.objs_or_paths:
                var_names_repr = ", ".join(feedback.objs_or_paths)
                return obs + f'("{feedback.text}", variables=[{var_names_repr}]")'

            return obs + f'("{feedback.text}")'

        if isinstance(feedback, FileObjModifiedFeedback):
            text = FILE_OBJ_MODIFIED_FEEDBACK_TEXT_TEMPLATE.format(
                varname=feedback.varname
            )
            return obs + f'("{text}")'

        if isinstance(feedback, UnassignedValueFeedback):
            text = UNASSIGNED_VALUE_FEEDBACK_TEXT_TEMPLATE.format(
                func_name=feedback.func_name, ret_anno=feedback.ret_anno
            )
            return obs + f'("{text}")'

        if isinstance(feedback, UnexpectedErrorFeedback):
            text = UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE.format(
                func_name=feedback.func_name
            )
            return obs + f'("{text}")'

        if isinstance(feedback, IncompleteCycleFeedback):
            return obs + f'("{INCOMPLETE_CYCLE_FEEDBACK_TEXT}")'

        raise ValueError(f"Unknown execution feedback: {feedback}")

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

    def _create_commmands_str(self, blocks: List[str]) -> str:
        return "\n".join(blocks)
