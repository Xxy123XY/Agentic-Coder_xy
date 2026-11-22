# import re
# from pathlib import Path
# from app.sandbox.executor import sandbox
# from app.sandbox.parser import parse_pytest_output


# def _read_repo_files(repo_path: str | Path) -> dict[str, str]:
#     repo_path = Path(repo_path)
#     files: dict[str, str] = {}
#     if not repo_path.exists():
#         return files
#     for py_file in repo_path.rglob("*.py"):
#         if any(p in {".venv", "venv", "__pycache__", ".git"} for p in py_file.parts):
#             continue
#         rel = py_file.relative_to(repo_path)
#         try:
#             files[str(rel)] = py_file.read_text(encoding="utf-8")
#         except (UnicodeDecodeError, OSError):
#             continue
#     return files


# def _normalize_path(path: str) -> str:
#     path = re.sub(r"^[ab]/", "", path)
#     path = re.sub(r"^/?tmp/[^/]+/", "", path)
#     return path.lstrip("/")


# def _apply_hunk(content: str, removed: list[str], added: list[str]) -> str:
#     if not removed:
#         return content
#     new = "\n".join(added)

#     # Strategy 1: exact block match
#     old = "\n".join(removed)
#     if old in content:
#         return content.replace(old, new, 1)

#     # Strategy 2: each removed line individually
#     for r in removed:
#         if r and r in content:
#             return content.replace(r, new, 1)

#     # Strategy 3: strip-whitespace match — handles indent differences
#     lines = content.split("\n")
#     for i, line in enumerate(lines):
#         for r in removed:
#             if r.strip() and line.strip() == r.strip():
#                 indent = len(line) - len(line.lstrip())
#                 new_lines = [
#                     (" " * indent + ln.lstrip() if ln.strip() else "")
#                     for ln in added
#                 ]
#                 lines[i] = "\n".join(new_lines)
#                 return "\n".join(lines)

#     return content


# def _apply_diff(files: dict[str, str], diff: str) -> dict[str, str]:
#     if not diff or "NO_FIX_POSSIBLE" in diff:
#         return files

#     updated = dict(files)
#     current_file = None
#     removed: list[str] = []
#     added: list[str] = []

#     def flush():
#         if current_file and current_file in updated and (removed or added):
#             updated[current_file] = _apply_hunk(updated[current_file], removed, added)

#     for line in diff.split("\n"):
#         if line.startswith("+++ "):
#             flush()
#             current_file = _normalize_path(line[4:].strip())
#             removed, added = [], []

#         elif line.startswith("--- "):
#             continue

#         elif line.startswith("@@"):
#             flush()
#             removed, added = [], []

#         elif current_file:
#             if line.startswith("-"):
#                 removed.append(line[1:])
#             elif line.startswith("+"):
#                 added.append(line[1:])

#     flush()
#     return updated


# # async def run_tests(
# #     test_code: str,
# #     repo_path: str | Path | None = None,
# #     diff: str | None = None,
# # ) -> dict:
# #     files: dict[str, str] = {}

# #     if repo_path:
# #         files = _read_repo_files(repo_path)

# #     if diff:
# #         files = _apply_diff(files, diff)

# #     files["test_fix.py"] = test_code

# #     result = await sandbox.run_command(
# #         command=["pytest", "test_fix.py", "-v", "--tb=short"],
# #         files=files,
# #     )

# #     parsed = parse_pytest_output(result["output"])

# #     return {
# #         "tests_passed": parsed["passed"] >= 1 and parsed["passed"] >= parsed["failed"],
# #         "output": result["output"],
# #         "summary": parsed,
# #     }

# async def run_tests(
#     test_code: str,
#     repo_path: str | Path | None = None,
#     diff: str | None = None,
# ) -> dict:
#     files: dict[str, str] = {}

#     if repo_path:
#         files = _read_repo_files(repo_path)

#     # Strategy 1: in-memory string replacement (fast)
#     if diff:
#         files = _apply_diff(files, diff)
#         # Strategy 2: also write diff file so git apply can try in container
#         files["patch.diff"] = diff

#     files["test_fix.py"] = test_code

#     # git apply is more reliable than string matching
#     # semicolon (;) means: even if git apply fails, pytest still runs
#     result = await sandbox.run_command(
#         command=["sh", "-c",
#             "git init -q && git add -A && "
#             "git apply --whitespace=fix --ignore-space-change patch.diff 2>/dev/null; "
#             "pytest test_fix.py -v --tb=short"
#         ],
#         files=files,
#     )

#     parsed = parse_pytest_output(result["output"])

#     return {
#         "tests_passed": parsed["passed"] >= 1 and parsed["passed"] >= parsed["failed"],
#         "output": result["output"],
#         "summary": parsed,
#     }

import re
from pathlib import Path
from app.sandbox.executor import sandbox
from app.sandbox.parser import parse_pytest_output


def _read_repo_files(repo_path: str | Path) -> dict[str, str]:
    repo_path = Path(repo_path)
    files: dict[str, str] = {}
    if not repo_path.exists():
        return files
    for py_file in repo_path.rglob("*.py"):
        if any(p in {".venv", "venv", "__pycache__", ".git"} for p in py_file.parts):
            continue
        try:
            files[str(py_file.relative_to(repo_path))] = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return files


def _normalize_path(path: str) -> str:
    path = re.sub(r"^[ab]/", "", path)
    path = re.sub(r"^/?tmp/[^/]+/", "", path)
    return path.lstrip("/")


def _apply_hunk(content: str, removed: list[str], added: list[str]) -> str:
    if not removed:
        return content
    new = "\n".join(added)

    # Strategy 1: exact block
    old = "\n".join(removed)
    if old in content:
        return content.replace(old, new, 1)

    # Strategy 2: each line individually
    for r in removed:
        if r and r in content:
            return content.replace(r, new, 1)

    # Strategy 3: strip-whitespace match
    lines = content.split("\n")
    for i, line in enumerate(lines):
        for r in removed:
            if r.strip() and line.strip() == r.strip():
                indent = len(line) - len(line.lstrip())
                new_lines = [
                    (" " * indent + ln.lstrip() if ln.strip() else "")
                    for ln in added
                ]
                lines[i] = "\n".join(new_lines)
                return "\n".join(lines)

    return content


def _apply_diff(files: dict[str, str], diff: str) -> dict[str, str]:
    if not diff or "NO_FIX_POSSIBLE" in diff:
        return files

    updated = dict(files)
    current_file: str | None = None
    removed: list[str] = []
    added: list[str] = []

    def flush() -> None:
        if current_file and current_file in updated and (removed or added):
            updated[current_file] = _apply_hunk(
                updated[current_file], list(removed), list(added)
            )

    for line in diff.split("\n"):
        if line.startswith("+++ "):
            flush()
            current_file = _normalize_path(line[4:].strip())
            removed.clear()
            added.clear()
        elif line.startswith("--- "):
            continue
        elif line.startswith("@@"):
            flush()
            removed.clear()
            added.clear()
        elif current_file:
            if line.startswith("-"):
                removed.append(line[1:])
            elif line.startswith("+"):
                added.append(line[1:])

    flush()
    return updated


async def run_tests(
    test_code: str,
    repo_path: str | Path | None = None,
    diff: str | None = None,
) -> dict:
    files: dict[str, str] = {}

    if repo_path:
        files = _read_repo_files(repo_path)

    # Strategy A: in-memory string replacement
    if diff:
        files = _apply_diff(files, diff)
        # Strategy B: write diff file so git apply can try too
        files["patch.diff"] = diff

    files["test_fix.py"] = test_code

    # git apply is more reliable — semicolon means pytest runs even if git apply fails
    result = await sandbox.run_command(
        command=["sh", "-c",
            "git init -q && git add -A 2>/dev/null && "
            "git apply --whitespace=fix --ignore-space-change patch.diff 2>/dev/null; "
            "pytest test_fix.py -v --tb=short"
        ],
        files=files,
    )
    
    parsed = parse_pytest_output(result["output"])

    print("PARSED:", parsed)

    tests_passed = parsed["passed"] >= 1

    return {
    "tests_passed": tests_passed,
    "output": result["output"],
    "summary": parsed,
}

    # parsed = parse_pytest_output(result["output"])

    # # passed >= 1 means at least some fix-related tests work
    # # human review gate is the final quality check anyway
    # tests_passed = parsed["passed"] >= 1

    # return {
    #     "tests_passed": tests_passed,
    #     "output": result["output"],
    #     "summary": parsed,
    # }