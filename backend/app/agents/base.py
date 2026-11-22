from abc import ABC, abstractmethod
from typing import Any
from app.observability.logger import get_logger


class BaseAgent(ABC):
    """Every agent inherits from this — guarantees same shape across all 6."""

    name: str = "base"

    def __init__(self):
        self.logger = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Read from state, do the work, return partial state update."""
        ...

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph calls agent(state) — we wrap with logging + error handling."""
        self.logger.info("agent_started", state_keys=list(state.keys()))
        try:
            update = await self.run(state)
            self.logger.info("agent_completed", output_keys=list(update.keys()))
            return update
        except Exception as e:
            self.logger.error("agent_failed", error=str(e), exc_info=True)
            return {"error_message": f"{self.name} failed: {e}"}