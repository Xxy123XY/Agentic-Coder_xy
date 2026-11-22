from typing import TypedDict, Annotated
from operator import add


class AgentState(TypedDict, total=False):
    """The single source of truth — every agent reads from and writes to this."""

    # Input (set when pipeline starts)
    job_id: str
    repo_full_name: str
    issue_number: int
    issue_url: str
    issue_title: str
    issue_body: str

    # IssueAnalyzer output
    issue_analysis: dict

    # CodebaseExplorer output
    relevant_files: list[dict]
    code_context: str

    # FixDrafter output
    proposed_diff: str

    # TestWriter output
    test_code: str

    # Validator output
    validation_passed: bool
    validation_errors: list[str]

    # Sandbox output
    tests_passed: bool
    test_output: str

    # PRCreator output
    pr_url: str

    # Control flow
    retry_count: int
    error_message: str
    human_approved: bool

    # Event log (multiple agents append to it — `add` reducer concatenates)
    events: Annotated[list[dict], add]