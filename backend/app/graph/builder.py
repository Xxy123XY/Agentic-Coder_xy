from langgraph.graph import StateGraph, START, END
from app.graph.state import AgentState
from app.graph.edges import (
    route_after_validator,
    route_after_sandbox,
    route_after_human,
    increment_retry,
)
from app.agents.issue_analyzer import issue_analyzer
from app.agents.codebase_explorer import codebase_explorer
from app.agents.fix_drafter import fix_drafter
from app.agents.test_writer import test_writer
from app.agents.validator import validator
from app.agents.pr_creator import pr_creator
from app.sandbox.runner import run_tests


# async def sandbox_node(state: dict) -> dict:
#     """Sandbox is not an agent — it's a tool. We wrap it as a graph node here."""
#     result = await run_tests(test_code=state.get("test_code", ""))
#     return {
#         "tests_passed": result["tests_passed"],
#         "test_output": result["output"],
#         "events": [{
#             "agent": "sandbox",
#             "type": "completed" if result["tests_passed"] else "failed",
#             "summary": f"Pytest: {result['summary']['passed']} passed, {result['summary']['failed']} failed",
#         }],
#     }
# async def sandbox_node(state: dict) -> dict:
#     """Sandbox is not an agent — it's a tool. We wrap it as a graph node here."""
#     # Local repo path — in dev we use /tmp/{repo_name}
#     repo_name = state.get("repo_full_name", "").split("/")[-1]
#     repo_path = f"/tmp/{repo_name}"

#     result = await run_tests(
#         test_code=state.get("test_code", ""),
#         repo_path=repo_path,
#     )
#     return {
#         "tests_passed": result["tests_passed"],
#         "test_output": result["output"],
#         "events": [{
#             "agent": "sandbox",
#             "type": "completed" if result["tests_passed"] else "failed",
#             "summary": f"Pytest: {result['summary']['passed']} passed, {result['summary']['failed']} failed",
#         }],
#     }
async def sandbox_node(state: dict) -> dict:
    repo_name = state.get("repo_full_name", "").split("/")[-1]
    repo_path = f"/tmp/{repo_name}"

    result = await run_tests(
        test_code=state.get("test_code", ""),
        repo_path=repo_path,
        diff=state.get("proposed_diff", ""),
    )
    return {
        "tests_passed": result["tests_passed"],
        "test_output": result["output"],
        "events": [{
            "agent": "sandbox",
            "type": "completed" if result["tests_passed"] else "failed",
            "summary": f"Pytest: {result['summary']['passed']} passed, {result['summary']['failed']} failed",
        }],
    }


async def human_review_node(state: dict) -> dict:
    """Placeholder — actual interrupt() happens via graph.compile(interrupt_before=...)."""
    return {}


def build_graph():
    """Construct the full LangGraph pipeline."""
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("issue_analyzer", issue_analyzer)
    graph.add_node("codebase_explorer", codebase_explorer)
    graph.add_node("fix_drafter", fix_drafter)
    graph.add_node("test_writer", test_writer)
    graph.add_node("validator", validator)
    graph.add_node("sandbox", sandbox_node)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("human_review", human_review_node)
    graph.add_node("pr_creator", pr_creator)

    # Linear path from start through to validator
    graph.add_edge(START, "issue_analyzer")
    graph.add_edge("issue_analyzer", "codebase_explorer")
    graph.add_edge("codebase_explorer", "fix_drafter")
    graph.add_edge("fix_drafter", "test_writer")
    graph.add_edge("test_writer", "validator")

    # After validator: pass → sandbox, fail → retry, max retries → end
    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {"sandbox": "sandbox", "retry": "increment_retry", "fail": END},
    )

    # After sandbox: tests pass → human review, fail → retry, max retries → end
    graph.add_conditional_edges(
        "sandbox",
        route_after_sandbox,
        {"human_review": "human_review", "retry": "increment_retry", "fail": END},
    )

    # Retry loops back to fix_drafter
    graph.add_edge("increment_retry", "fix_drafter")

    # After human decision: approve → PR creator, reject → end
    graph.add_conditional_edges(
        "human_review",
        route_after_human,
        {"pr_creator": "pr_creator", "end": END},
    )

    graph.add_edge("pr_creator", END)

    return graph


def compile_graph(checkpointer):
    """Compile graph with interrupt before human_review (for HITL gate)."""
    graph = build_graph()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )