from app.agents.base import BaseAgent
from app.github.pr import create_pull_request


class PRCreatorAgent(BaseAgent):
    name = "pr_creator"

    async def run(self, state: dict) -> dict:
        # Only proceed if human approved
        if not state.get("human_approved", False):
            return {
                "events": [{
                    "agent": self.name,
                    "type": "failed",
                    "summary": "Skipped: human did not approve",
                }],
            }

        pr_url = await create_pull_request(
            repo_full_name=state["repo_full_name"],
            issue_number=state["issue_number"],
            issue_title=state.get("issue_title", ""),
            diff=state["proposed_diff"],
            test_code=state.get("test_code", ""),
            analysis=state.get("issue_analysis", {}),
        )

        return {
            "pr_url": pr_url,
            "events": [{
                "agent": self.name,
                "type": "completed",
                "summary": f"PR opened: {pr_url}",
            }],
        }


pr_creator = PRCreatorAgent()