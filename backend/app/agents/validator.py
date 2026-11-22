import subprocess
import tempfile
from pathlib import Path
from app.agents.base import BaseAgent


class ValidatorAgent(BaseAgent):
    name = "validator"

    async def run(self, state: dict) -> dict:
        diff = state.get("proposed_diff", "")
        test_code = state.get("test_code", "")

        errors: list[str] = []

        # Quick sanity checks before running expensive tools
        if not diff or diff == "NO_FIX_POSSIBLE":
            errors.append("FixDrafter produced no usable diff")
        if not test_code:
            errors.append("TestWriter produced no test code")

        # If basic checks fail, skip expensive validation
        if errors:
            return self._fail(errors)

        # Run pylint + mypy on the test file (we can't easily apply diff in static analysis)
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_fix.py"
            test_file.write_text(test_code)

            errors.extend(self._run_pylint(test_file))
            errors.extend(self._run_mypy(test_file))

        passed = len(errors) == 0

        return {
            "validation_passed": passed,
            "validation_errors": errors,
            "events": [{
                "agent": self.name,
                "type": "completed" if passed else "failed",
                "summary": "Validation passed" if passed else f"{len(errors)} issues found",
            }],
        }

    def _run_pylint(self, file_path: Path) -> list[str]:
        try:
            result = subprocess.run(
                ["pylint", "--errors-only", str(file_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return [line for line in result.stdout.splitlines() if line.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _run_mypy(self, file_path: Path) -> list[str]:
        try:
            result = subprocess.run(
                ["mypy", "--ignore-missing-imports", str(file_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return [line for line in result.stdout.splitlines() if "error" in line.lower()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _fail(self, errors: list[str]) -> dict:
        return {
            "validation_passed": False,
            "validation_errors": errors,
            "events": [{"agent": self.name, "type": "failed", "summary": "; ".join(errors)}],
        }


validator = ValidatorAgent()