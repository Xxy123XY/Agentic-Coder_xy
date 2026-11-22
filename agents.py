# from pydantic.v1 import BaseModel as BaseModelV1
from prompts import coder_prompt,Testing_prompt,Planners_prompt
from dotenv import load_dotenv
import uuid
import os

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition

from typing import TypedDict

from langgraph.prebuilt import tools_condition

class AgentState(MessagesState):
    review_status: str

load_dotenv()

@tool
def read_file(file_path: str) -> str:
    """Read the contents of a text file."""

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

llm = ChatOpenAI(
    model="openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
coder_llm = llm.bind_tools([read_file])
tester_llm = llm.bind_tools([read_file])


def coding_router(state):
    if tools_condition(state) == "tools":
        return "coding_tools"

    return "testing"


def testing_routers(state):
    if tools_condition(state) == "tools":
        return "testing_tools"

    if state["review_status"] == "PASS":
        return "summary_model"

    return "coding_agent"



def Planner_prompt_llm(state: AgentState):
    messages = [
        SystemMessage(
            content=Planners_prompt
            )
    ] + state["messages"]

    response = llm.invoke(messages)

    return {
        "messages": [response]
    }

def coding_agent(state: AgentState):
    messages = [
        SystemMessage(content=coder_prompt)
    ] + state["messages"]

    response = coder_llm.invoke(messages)

    # Only save code if the model actually generated code.
    if not response.tool_calls:
        with open("coder.py", "w", encoding="utf-8") as f:
            f.write(response.content)

    return {
        "messages": [response]
    }
def testing(state: AgentState):
    messages = [
        SystemMessage(content=Testing_prompt)
    ] + state["messages"]

    response = tester_llm.invoke(messages)

    # If the model wants to call a tool,
    # don't evaluate PASS/FAIL yet.
    if response.tool_calls:
        return {
            "messages": [response]
        }

    status = "PASS" if response.content.strip() == "PASS" else "FAIL"

    return {
        "messages": [response],
        "review_status": status
    }
def summary_model(state:AgentState):
    messages = [
        SystemMessage(
            content="You have to sumarize this whole convesation below in bullets"
        ) 
    ] + state["messages"]
    response = llm.invoke(messages)
    with open("testing.txt", "w", encoding="utf-8") as file:
        file.write(response.content)
    return


checkpointer = InMemorySaver()

graph_builder = StateGraph(AgentState)

# tool_node = ToolNode([read_file])

graph_builder.add_node(Planner_prompt_llm)
graph_builder.add_node(coding_agent)
graph_builder.add_node(testing)
graph_builder.add_node(summary_model)
coding_tools = ToolNode([read_file])
testing_tools = ToolNode([read_file])

graph_builder.add_node("coding_tools", coding_tools)
graph_builder.add_node("testing_tools", testing_tools)
graph_builder.add_edge(START, "Planner_prompt_llm")
graph_builder.add_edge("Planner_prompt_llm", "coding_agent")
graph_builder.add_conditional_edges(
    "coding_agent",
    coding_router,
    {
        "coding_tools": "coding_tools",
        "testing": "testing",
    }
)

graph_builder.add_edge(
    "coding_tools",
    "coding_agent"
)

graph_builder.add_conditional_edges(
    "testing",
    testing_routers,
    {
        "testing_tools": "testing_tools",
        "coding_agent": "coding_agent",
        "summary_model": "summary_model",
    }
)

graph_builder.add_edge(
    "testing_tools",
    "testing"
)


graph_builder.add_edge("summary_model",END)
graph = graph_builder.compile(checkpointer=checkpointer)
graph.get_graph().draw_mermaid_png(output_file_path="graph.png")


config = { 'configurable': { 'thread_id': str(uuid.uuid4()) } }

while True:
    user_message = input("Enter message: ")
    response = graph.invoke({"messages": [{"role": "user", "content": user_message}]}, config=config)
     # print("Response:", response["messages"][-1].content)

        