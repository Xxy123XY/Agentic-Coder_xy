from app.agents.base import BaseAgent
from app.llm.router import llm_router
from app.schemas.issue import IssueAnalysis


SYSTEM_PROMPT = """You are an expert software triage engineer.
Read a GitHub issue and extract structured information.

Return JSON with these exact fields:
- module: primary code module affected (e.g. "auth", "payments", "api")
- severity: one of "low", "medium", "high", "critical"
- repro_steps: list of steps to reproduce, as strings
- expected_behavior: what should happen
- actual_behavior: what actually happens
- keywords: 3-5 search keywords for finding relevant code files

If the issue is vague, infer reasonable values. Never leave fields empty."""


class IssueAnalyzerAgent(BaseAgent):
    name = "issue_analyzer"

    async def run(self, state: dict) -> dict:
        title = state.get("issue_title", "")
        body = state.get("issue_body", "")

        user_message = f"Title: {title}\n\nBody:\n{body}"

        result = await llm_router.complete(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            task="extraction",
            json_mode=True,
        )

        # Pydantic validates the LLM output
        analysis = IssueAnalysis(**result)

        return {
            "issue_analysis": analysis.model_dump(),
            "events": [{
                "agent": self.name,
                "type": "completed",
                "summary": f"Severity: {analysis.severity}, Module: {analysis.module}",
            }],
        }


issue_analyzer = IssueAnalyzerAgent()