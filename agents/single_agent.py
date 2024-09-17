from typing import Annotated, Literal
from datetime import datetime
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import AnyMessage, add_messages
from langchain_openai import ChatOpenAI

import tools.tnb as tnb_tools
import tools.ocr as ocr_tools
import tools.database as db_tools
from components.utilities import create_tool_node_with_fallback
from components.checkpointer import MongoDBSaver, MongoClient, AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient

import components.initializer as init

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    async def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = await self.runnable.ainvoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


checkpointer = AsyncMongoDBSaver(
    AsyncIOMotorClient(init.CHATBOT_MONGO_CONNECTION_STRING), init.CHATBOT_MONGO_DATABASE, init.CHATBOT_MONGO_COLLECTION)

llm = ChatOpenAI(openai_api_key=init.OPENAI_API_KEY, model=init.DEFAULT_CHAT_MODEL)

assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful customer support assistant for Sunway group. "
            " Use the provided tools to assist the user's queries."
            " When searching, be persistent. Expand your query bounds if the first search returns no results. "
            " If a search comes up empty, expand your search before giving up."
            " When calling a tool that requries a certain parameter, ask the user every single time for the parameter, do not use the parameters from previous tool calls "
            " After using a tool, make sure to show the string output of the tool to the user, indicating that the tool is successfully called and used "
            " Don't bold your answers to the assistant prompt."
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

"""
This section establishes all the safe/sensitive tools and that managers and non-managers have access
"""
manager_safe_tools = [
    TavilySearchResults(max_results=1),
    tnb_tools.agent_get_statement_information,
    tnb_tools.agent_get_all_account_names,
    db_tools.determine_db_to_query_tool,
    db_tools.python_repl_tool,
    ocr_tools.agent_utilise_ocr,
    ocr_tools.agent_validate_file,
    tnb_tools.agent_edit_tnb_meter_application,
    tnb_tools.agent_fill_up_tnb_meter_application
]

manager_sensitive_tools = [
    tnb_tools.agent_retrieve_monthly_bill_pdf,
    tnb_tools.agent_get_electricity_info_for_month,
]

non_manager_safe_tools = [
    TavilySearchResults(max_results=1),
    tnb_tools.agent_get_statement_information,
    tnb_tools.agent_get_all_account_names,
    db_tools.determine_db_to_query_tool,
    db_tools.python_repl_tool,
    ocr_tools.agent_utilise_ocr,
    ocr_tools.agent_validate_file,
    tnb_tools.agent_edit_tnb_meter_application,
    tnb_tools.agent_fill_up_tnb_meter_application
]

non_manager_sensitive_tools = [
    tnb_tools.agent_retrieve_monthly_bill_pdf,
    tnb_tools.agent_get_electricity_info_for_month,
]

# Provides differnet tools to agent depneding on manager status
def check_manager(manager_status):
    if manager_status == "manager":
        sensitive_tools = {t.name for t in manager_sensitive_tools}
        # Our LLM doesn't have to know which nodes it has to route to. In its 'mind', it's just invoking functions.
        single_agent_assistant_runnable = assistant_prompt | llm.bind_tools(
            manager_safe_tools + manager_sensitive_tools
        )
        return single_agent_assistant_runnable, manager_safe_tools, manager_sensitive_tools
    
    else:
        sensitive_tools = {t.name for t in non_manager_safe_tools}
        # Our LLM doesn't have to know which nodes it has to route to. In its 'mind', it's just invoking functions.
        single_agent_assistant_runnable = assistant_prompt | llm.bind_tools(
            non_manager_safe_tools + non_manager_sensitive_tools
        )
        return single_agent_assistant_runnable, non_manager_safe_tools, non_manager_sensitive_tools

single_agent_assistant_runnable, single_agent_safe_tools, single_agent_sensitive_tools = check_manager(init.MANAGER_STATUS)

# DEFINE THE GRAPH
builder = StateGraph(State)
builder.add_node("assistant", Assistant(single_agent_assistant_runnable))
builder.add_node("safe_tools", create_tool_node_with_fallback(single_agent_safe_tools))
builder.add_node(
    "sensitive_tools", create_tool_node_with_fallback(single_agent_sensitive_tools)
)

sensitive_tools = {t.name for t in non_manager_sensitive_tools + manager_sensitive_tools}
def route_tools(state: State) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    next_node = tools_condition(state)
    # If no tools are invoked, return to the user
    if next_node == END:
        return END
    ai_message = state["messages"][-1]
    # This assumes single tool calls. To handle parallel tool calling, you'd want to
    # use an ANY condition
    first_tool_call = ai_message.tool_calls[0]
    if first_tool_call["name"] in sensitive_tools:
        return "sensitive_tools"
    return "safe_tools"

builder.add_conditional_edges(
    "assistant",
    route_tools,
)
builder.add_edge(START, "assistant")
builder.add_edge("safe_tools", "assistant")
builder.add_edge("sensitive_tools", "assistant")


memory = AsyncSqliteSaver.from_conn_string(":memory:")
single_agent_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["sensitive_tools"],
)
