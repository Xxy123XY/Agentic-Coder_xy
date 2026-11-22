# import re


# def parse_pytest_output(output: str) -> dict:
#     """Extract structured info from pytest stdout.

#     Returns: {passed, failed, errors, total, failures}
#     """
#     summary_pattern = re.compile(
#         r"(?:(\d+) passed)?(?:.*?(\d+) failed)?(?:.*?(\d+) error)?",
#         re.IGNORECASE,
#     )

#     passed = failed = errors = 0
#     for line in output.splitlines():
#         if "passed" in line or "failed" in line or "error" in line:
#             match = summary_pattern.search(line)
#             if match:
#                 passed = int(match.group(1) or 0)
#                 failed = int(match.group(2) or 0)
#                 errors = int(match.group(3) or 0)

#     # Extract failure messages (lines starting with FAILED or ERROR)
#     failures = [
#         line for line in output.splitlines()
#         if line.startswith("FAILED") or line.startswith("ERROR")
#     ]

#     return {
#         "passed": passed,
#         "failed": failed,
#         "errors": errors,
#         "total": passed + failed + errors,
#         "failures": failures,
#     }

# gpt code

import re


def parse_pytest_output(output: str) -> dict:
    passed = failed = errors = 0

    summary_match = re.search(
        r"=+.*?(\d+\s+passed.*?|"
        r"\d+\s+failed.*?|"
        r"\d+\s+error.*?).*?=+",
        output,
        re.IGNORECASE | re.DOTALL,
    )

    if summary_match:
        summary = summary_match.group(0)

        p = re.search(r"(\d+)\s+passed", summary, re.I)
        f = re.search(r"(\d+)\s+failed", summary, re.I)
        e = re.search(r"(\d+)\s+errors?", summary, re.I)

        passed = int(p.group(1)) if p else 0
        failed = int(f.group(1)) if f else 0
        errors = int(e.group(1)) if e else 0

    failures = [
        line
        for line in output.splitlines()
        if line.startswith("FAILED")
        or line.startswith("ERROR")
    ]

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": passed + failed + errors,
        "failures": failures,
    }