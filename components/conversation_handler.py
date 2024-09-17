import uuid
from langchain_core.messages import ToolMessage
from components.utilities import _print_event
import tools.ocr as ocr_tools
import components.initializer as init
from pymongo import MongoClient
from fastapi import UploadFile
from typing import List
from agents.single_agent import single_agent_graph
from components.initializer import mongo_client as client

db = client[init.CHATBOT_MONGO_DATABASE]
collection = db[init.CHATBOT_MONGO_COLLECTION_STATUS]


async def handle_single_agent_1(user_input: str, thread_id):
    print("1")
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    _printed = set()
    tool_call_id = "None"   
    events = single_agent_graph.astream(
        {"messages": ("user", user_input)}, config, stream_mode="values"
    )
    async for event in events:
        _print_event(event, _printed)

        # Return the last event message
        message = event.get("messages")
        if message:
            if isinstance(message, list):
                message = message[-1]
                last_msg = message.content

    snapshot = await single_agent_graph.aget_state(config)

    if snapshot.next:
        ask_permission = "ask permission"
        tool_call_name = event["messages"][-1].tool_calls[0]["name"]
        tool_call_ids = [tc["id"] for tc in event["messages"][-1].tool_calls]
        response = "Do you approve the use of the tool? Type in (yes/no) \nTool Called: " + tool_call_name
        return ask_permission, response, tool_call_ids

    ask_permission = "new"
    return ask_permission, last_msg, tool_call_id

# returns last_msg, ask_permission
async def handle_single_agent_2(user_input: str, ask_permission: str, tool_call_ids: List[str], thread_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    snapshot = await single_agent_graph.aget_state(config)
    user_input = user_input.lower()

    while snapshot.next and ask_permission == "ask permission":
        if user_input == "yes":
            print("in response yes")
            event = await single_agent_graph.ainvoke(None, config)

        else:
            print("In response no")
            tool_messages = [
            ToolMessage(
                content="API call denied by user. Continue assisting, accounting for the user's input.",
                tool_call_id=id,
            )
            for id in tool_call_ids
            ]

            event = await single_agent_graph.ainvoke(
                {
                    "messages": tool_messages
                },
                config,
            )

        snapshot = await single_agent_graph.aget_state(config)
    
    message = event.get("messages")
    # print(message)
    if message:
        if isinstance(message, list):
            message = message[-1]
            last_msg = message.content
    ask_permission = "new"
    return last_msg, ask_permission


async def handle_single_agent_all(user_input: str, thread_id: str, file: UploadFile = None):
    permission, tool_call_id = await get_status(thread_id=thread_id)
  
    if file is not None:
        link = await ocr_tools.upload_file_and_get_link(file)
        user_input = user_input + " " + link

    if permission == "ask permission":
        response, permission = await handle_single_agent_2(user_input=user_input, ask_permission=permission, tool_call_ids=tool_call_id, thread_id=thread_id)

    # New input from the user
    elif permission == "new":
        permission, response, tool_call_id = await handle_single_agent_1(user_input, thread_id)

    elif permission == "finish":
        permission = "new"

    # Update the permission and tool_call_id on mongodb
    await update_status(thread_id, permission, tool_call_id)
    return response


async def get_status(thread_id: str) -> str:
    """
    gets and uploads status of the user from MongoDB
    """
    # Retrieve the status document from MongoDB
    print("Fetching status...")
    status = await collection.find_one({"thread_id": thread_id})  # Replace with your document's _id or any identifier
    if status is None:
        status = {"thread_id": thread_id, "permission": "new", "tool_call_id": "None"}
        await collection.insert_one(status)
    
    permission = status["permission"]
    tool_call_id = status["tool_call_id"]

    print("returning status")
    return permission, tool_call_id


async def update_status(thread_id, permission, tool_call_id) -> None:
    """
    updates the status for user on mongodb
    """
    # Prepare the fields to update
    update_fields = {
        "permission": permission,
        "tool_call_id": tool_call_id
    }

    # Update the document in MongoDB
    await collection.update_one(
        {"thread_id": thread_id},
        {"$set": update_fields},
        upsert=True
    )


"""
Multi-agent, work in progress
"""
# def handle_multi_agent_1(user_input: str):
#     _printed = set()
#     ask_permission = "no permission"
#     tool_call_id = tool_call_name = "None"
#     events = multi_agent_graph.stream(
#         {"messages": ("user", user_input)}, config, stream_mode="values"
#     )
#     for event in events:
#         _print_event(event, _printed)

#         # Return the last event message
#         message = event.get("messages")
#         if message:
#             if isinstance(message, list):
#                 message = message[-1]
#                 last_msg = message.content

#     snapshot = multi_agent_graph.get_state(config)

#     if snapshot.next:
#         print("In snapshot next")
#         ask_permission = "ask permission"
#         tool_call_id = event["messages"][-1].tool_calls[0]["id"]
#         tool_call_name = event["messages"][-1].tool_calls[0]["name"]

#     return ask_permission, event, tool_call_id, tool_call_name

# # returns last_msg, ask_permission
# def handle_multi_agent_2(user_input: str, event: str, tool_call_id: str, ask_permission: str):
#     snapshot = multi_agent_graph.get_state(config)
#     user_input = user_input.lower()

#     while snapshot.next and ask_permission == "ask permission":
#         if user_input == "yes":
#             print("in response yes")
#             event = multi_agent_graph.invoke(None, config)

#         else:
#             print("In response no")
#             tool_call_ids = [tc["id"] for tc in event["messages"][-1].tool_calls]
#             print(tool_call_ids)

#             # Create a list of ToolMessages, one for each tool call
#             tool_messages = [
#                 ToolMessage(
#                     content=f"API call denied by user. Continue assisting, accounting for the user's input.",
#                     tool_call_id=my_id,
#                 )
#                 for my_id in tool_call_ids
#             ]
            
#             event = multi_agent_graph.invoke(
#                 {
#                     "messages": tool_messages
#                 },
#                 config,
#             )

#         snapshot = multi_agent_graph.get_state(config)
    
#     message = event.get("messages")
#     if message:
#         if isinstance(message, list):
#             message = message[-1]
#             last_msg = message.content
#     ask_permission = "finish"
#     return last_msg, ask_permission