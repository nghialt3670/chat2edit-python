import pickle
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel

from chat2edit.base.context_provider import ContextProvider
from chat2edit.base.file_storage import FileStorage
from chat2edit.base.llm import Llm
from chat2edit.base.prompt_strategy import PromptStrategy
from chat2edit.constants import (
    EXECUTION_CONTEXT_FILE_EXTENSION,
    EXECUTION_CONTEXT_FILE_MIME_TYPE,
    FILE_SRC_TO_PATHS_KEY,
    MAX_VARNAME_SEARCH_INDEX,
    OBJ_ID_TO_VARNAME_KEY,
    SYSTEM_FILE_STORAGE_FOR_CONTEXT_FILES_SAVE_DIR,
    SYSTEM_FILE_STORAGE_FOR_RESPONSE_FILES_SAVE_DIR,
)
from chat2edit.execution.execute import execute
from chat2edit.models.cobject import ContextObject, FileObject
from chat2edit.models.cycles import ChatCycle, PromptCycle
from chat2edit.models.file import File
from chat2edit.models.messages import ChatMessage, ContextMessage
from chat2edit.prompting.prompt import prompt
from chat2edit.prompting.strategies.otc_strategy import OtcStrategy
from chat2edit.storages.system_file_storage import SystemFileStorage
from chat2edit.utils.context import path_to_obj
from chat2edit.utils.pickle import is_pickleable


class Chat2EditConfig(BaseModel):
    max_pc_per_cc: int
    max_cc_per_p: int
    max_p_per_pc: int


DEFAULT_STRATEGY = OtcStrategy()
DEFAULT_REQ_STORAGE = SystemFileStorage("")
DEFAULT_RES_STORAGE = SystemFileStorage(SYSTEM_FILE_STORAGE_FOR_RESPONSE_FILES_SAVE_DIR)
DEFAULT_CTX_STORAGE = SystemFileStorage(SYSTEM_FILE_STORAGE_FOR_CONTEXT_FILES_SAVE_DIR)
DEFAULT_CONFIG = Chat2EditConfig(max_pc_per_cc=4, max_cc_per_p=10, max_p_per_pc=2)
DEFAULT_EXEC_CONTEXT = {
    FILE_SRC_TO_PATHS_KEY: {},
    OBJ_ID_TO_VARNAME_KEY: {},
}


class Chat2Edit:
    def __init__(
        self,
        *,
        provider: ContextProvider,
        llm: Llm,
        strategy: PromptStrategy = DEFAULT_STRATEGY,
        req_storage: FileStorage = DEFAULT_REQ_STORAGE,
        res_storage: FileStorage = DEFAULT_RES_STORAGE,
        ctx_storage: FileStorage = DEFAULT_CTX_STORAGE,
        config: Chat2EditConfig = DEFAULT_CONFIG,
        history: List[ChatCycle] = [],
    ):
        self._provider = provider
        self._strategy = strategy
        self._llm = llm
        self._req_storage = req_storage
        self._res_storage = res_storage
        self._ctx_storage = ctx_storage
        self._config = config
        self._history = history
        self._exec_context = self._init_exec_context()

    def set_history(self, history: List[ChatCycle]) -> None:
        self._history = history

    def get_history(self) -> List[ChatCycle]:
        return self._history

    def clear_hisotry(self) -> None:
        self._history = []

    def pop_cycle(self) -> None:
        self._history.pop()

    async def response(self, message: ChatMessage) -> Optional[ChatMessage]:
        request = await self._create_request_from_message(message)

        chat_cycle = ChatCycle(req_message=message, request=request)
        valid_cycles = [c for c in self._history if c.res_message]

        if valid_cycles:
            await self._load_exec_context()

        main_cycles = valid_cycles[-self._config.max_cc_per_p :] + [chat_cycle]

        while len(chat_cycle.prompt_cycles) < self._config.max_pc_per_cc:
            prompting_result = await prompt(
                cycles=main_cycles,
                llm=self._llm,
                strategy=self._strategy,
                context=self._provider.get_context(),
                max_prompts=self._config.max_p_per_pc,
            )

            prompt_cycle = PromptCycle(prompting_result)
            chat_cycle.prompt_cycles.append(prompt_cycle)

            code = prompting_result.code
            if not code:
                break

            execution_result = await execute(code, self._exec_context)
            prompt_cycle.execution_result = execution_result

            if execution_result.error:
                break

            response = execution_result.response
            if response:
                res_messsage = await self._create_message_from_response(response)
                chat_cycle.exec_context_src = await self._save_exec_context()
                chat_cycle.res_message = res_messsage
                break

        self._history.append(chat_cycle)
        return chat_cycle.res_message

    async def _create_request_from_message(self, message: ChatMessage) -> List[str]:
        paths = []

        for src in message.file_srcs:
            if src in self._exec_context[FILE_SRC_TO_PATHS_KEY]:
                paths = self._exec_context[FILE_SRC_TO_PATHS_KEY][src]
            else:
                file = await self._req_storage.load(src)
                obj = self._provider.load_file_obj(file)
                paths = self._assign_file_obj(obj)

                self._exec_context[FILE_SRC_TO_PATHS_KEY][src] = paths

        return ContextMessage(text=message.text, objs_or_paths=paths)

    async def _create_message_from_response(
        self, response: ContextMessage
    ) -> List[str]:
        file_srcs = []

        for varname in response.objs_or_paths:
            obj: ContextObject = path_to_obj(self._exec_context, varname)
            file = self._provider.save_file_obj(obj)
            src = await self._res_storage.save(file)
            file_srcs.append(src)

            self._exec_context[FILE_SRC_TO_PATHS_KEY][src] = obj.id
            self._exec_context[OBJ_ID_TO_VARNAME_KEY][obj.id] = varname

        return ChatMessage(text=response.text, file_srcs=file_srcs)

    def _assign_file_obj(self, file_obj: FileObject) -> List[str]:
        existing_varnames = set(self._exec_context.keys())
        file_obj_varname = None
        paths = []

        if file_obj.id in self._exec_context[OBJ_ID_TO_VARNAME_KEY]:
            file_obj_varname = self._exec_context[OBJ_ID_TO_VARNAME_KEY][file_obj.id]
            paths.append(file_obj_varname)
        else:
            file_obj_varname = self._find_suitable_varname(file_obj, existing_varnames)
            self._exec_context[OBJ_ID_TO_VARNAME_KEY][file_obj.id] = file_obj_varname
            paths.append(file_obj_varname)

        self._exec_context[file_obj_varname] = file_obj

        paths.extend([f"{file_obj_varname}.{path}" for path in file_obj.attr_paths])

        for query_obj in file_obj.query_objs:
            query_obj_varname = self._find_suitable_varname(
                query_obj, existing_varnames
            )
            self._exec_context[query_obj_varname] = query_obj
            paths.append(query_obj_varname)

        return paths

    def _find_suitable_varname(
        self, obj: ContextObject, existing_varnames: Set[str]
    ) -> str:
        for i in range(MAX_VARNAME_SEARCH_INDEX):
            varname = f"{obj.basename}{i}"
            if varname not in existing_varnames:
                return varname

        varname_id = str(uuid4).split("_").pop()
        return f"{obj.basename}{varname_id}"

    def _init_exec_context(self) -> Dict[str, Any]:
        exec_context = DEFAULT_EXEC_CONTEXT
        provided_context = self._provider.get_context()
        exec_context.update(provided_context.exec_context)
        return exec_context

    async def _load_exec_context(self) -> None:
        last_cycle = self._history[-1]
        file = await self._ctx_storage.load(last_cycle.exec_context_src)
        self._exec_context = pickle.loads(file.buffer)

    async def _save_exec_context(self) -> str:
        buffer = pickle.dumps(self._filter_exec_context())
        mimetype = EXECUTION_CONTEXT_FILE_MIME_TYPE
        extension = EXECUTION_CONTEXT_FILE_EXTENSION
        filename = f"{str(uuid4())}{extension}"
        file = File(mimetype, filename, buffer)
        return await self._ctx_storage.save(file)

    def _filter_exec_context(self) -> Dict[str, Any]:
        return {k: v for k, v in self._exec_context.items() if is_pickleable(v)}
