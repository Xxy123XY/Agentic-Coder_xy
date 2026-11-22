from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential
import json
from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        """Send messages to Groq, return text response."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"} if json_mode else None,
        )
        content = response.choices[0].message.content
        logger.info(
            "groq_call",
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        return content

    async def chat_json(self, messages: list[dict], model: str) -> dict:
        """Send messages to Groq, expect JSON response, return parsed dict."""
        raw = await self.chat(messages, model=model, json_mode=True)
        return json.loads(raw)


groq_client = GroqClient()