from app.agents.base import BaseAgent
from app.llm.router import llm_router


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text

# SYSTEM_PROMPT = """You write pytest test cases for code changes.

# You will receive a unified diff showing a code fix. Write pytest tests that:
# 1. Verify the fix actually resolves the bug (positive cases)
# 2. Cover edge cases (empty inputs, None, boundary conditions)
# 3. Use pytest fixtures and parametrize where appropriate

# Rules:
# - Output ONLY valid Python code, no markdown fences, no explanation
# - Start with necessary imports
# - Use descriptive test function names: test_<scenario>_<expected_outcome>
# - Include at least 3 test cases
# - Tests must be runnable with: pytest <filename>.py"""

# SYSTEM_PROMPT = """You write pytest test cases for code changes.

# You will receive a unified diff showing a code fix. Write pytest tests that:
# 1. Verify the fix actually resolves the bug (positive cases)
# 2. Cover edge cases (empty inputs, None, boundary conditions)
# 3. Use pytest fixtures and parametrize where appropriate

# Rules:
# - Output ONLY valid Python code, no markdown fences, no explanation
# - Start with necessary imports
# - Use descriptive test function names: test_<scenario>_<expected_outcome>
# - Include at least 3 test cases
# - Tests must be runnable with: pytest test_fix.py

# CRITICAL import rules — the sandbox working directory is /sandbox:
# - Files are placed at root: auth/login.py becomes importable as: from auth.login import ...
# - NEVER use prefixes like tmp., bug_test., /tmp/ in any import
# - NEVER use absolute paths in imports
# - If file is auth/login.py → import: from auth.login import login_user
# - If file is utils/validator.py → import: from utils.validator import is_valid_email
# - Always test through the public functions, not internal implementation"""

SYSTEM_PROMPT = """You write pytest test cases for code changes.

You will receive a unified diff showing a code fix. Write pytest tests that:

Verify the fix actually resolves the bug.
Include straightforward positive test cases that are highly likely to pass when the fix is correct.
Add reasonable edge-case coverage only when it is clearly supported by the code and diff.
Focus on validating expected behavior through the public API.

Rules:

Output ONLY valid Python code.
Do NOT include markdown fences.
Do NOT include explanations, comments, or extra text.
Start with all necessary imports.
Use descriptive test function names: test__<expected_outcome>
Prefer simple and robust assertions.
Avoid complex mocking unless required.
Avoid testing undocumented behavior.
Avoid making assumptions not supported by the diff.
Use pytest fixtures and parametrize when they improve clarity.
Tests must be runnable with: pytest test_fix.py

CRITICAL import rules — the sandbox working directory is /sandbox:

Files are placed at root: auth/login.py becomes importable as: from auth.login import ...
NEVER use prefixes like tmp., bug_test., /tmp/ in any import
NEVER use absolute paths in imports
If file is auth/login.py → import: from auth.login import login_user
If file is utils/validator.py → import: from utils.validator import is_valid_email
Always test through public functions, classes, and APIs rather than internal implementation details.

IMPORTANT:

The primary goal is to produce runnable tests that directly verify the bug fix.
Prefer a small number of reliable tests over many speculative tests.
When behavior is ambiguous, test only what is clearly implied by the diff.
Ensure at least one strong positive test case validates the intended fix.
"""


class TestWriterAgent(BaseAgent):
    name = "test_writer"

    async def run(self, state: dict) -> dict:
        analysis = state.get("issue_analysis", {})
        diff = state.get("proposed_diff", "")

        user_message = f"""Bug description:
{analysis.get('actual_behavior', '')}

Expected behavior:
{analysis.get('expected_behavior', '')}

Proposed fix (unified diff):
{diff}

Write pytest tests."""

        test_code = await llm_router.complete(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            task="reasoning",
        )
        test_code = _strip_fences(test_code)

        return {
            "test_code": test_code.strip(),
            "events": [{
                "agent": self.name,
                "type": "completed",
                "summary": f"Generated test file ({len(test_code)} chars)",
            }],
        }


test_writer = TestWriterAgent()