from typing import Literal
from app.config import get_settings
from app.llm.groq_client import groq_client

settings = get_settings()

TaskType = Literal["reasoning", "code", "extraction"]


class LLMRouter:
    """Picks the right model based on the task type."""

    def model_for(self, task: TaskType) -> str:
        if task == "code":
            return settings.groq_code_model
        return settings.groq_reason_model

    async def complete(
        self,
        messages: list[dict],
        task: TaskType,
        json_mode: bool = False,
    ) -> str | dict:
        model = self.model_for(task)
        if json_mode:
            return await groq_client.chat_json(messages, model=model)
        return await groq_client.chat(messages, model=model)


llm_router = LLMRouter()