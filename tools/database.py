from typing import Annotated
import uuid
import re
import base64
import io
import matplotlib
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_experimental.utilities import PythonREPL

import components.db as db
import components.gcs_bucket as gcs
import components.initializer as init

repl = PythonREPL()

# FUNCTIONS
async def determine_db_to_query(user_input):
    limit = 2
    res = init.openai_client.embeddings.create(input=user_input, model=init.DEFAULT_EMBEDDINGS_MODEL)
    embeddings = [data.embedding for data in res.data]

    # Find matching vectors
    aggregation_pipeline = [
        {
            "$vectorSearch": {
                "queryVector": embeddings[0],
                "path": "embeddings",
                "numCandidates": 100,
                "index": "db_description_vector_index",
                "limit": limit,
            }
        },   
        {
            "$project": {
                "_id": 0,
                "page_content": 1,
                "database_name": 1,  # Include the database name in the projection
                "score": {
                    "$meta": "vectorSearchScore"
                }
            }
        }
    ]
    collection = init.mongodb.get_collection("sql_db_description")
    matched_vectors = await collection.aggregate(aggregation_pipeline).to_list(length=None)
    print("\n\nMatched Vectors: " + str(matched_vectors))

    # Determine the database to query from the matched vectors
    if matched_vectors:
        db_choice = matched_vectors[0]['database_name']
        print("Database: " + db_choice)

        # Query the appropriate database based on the database_name
        if db_choice == "suria":
            result = await query_suria_sql_db(user_input)
        elif db_choice == "sip-cde":
            result = await query_sip_cde_sql_db(user_input)
        else:
            result = f"Error: No known database found for {db_choice}."
    else:
        result = "Error: No matched vectors found."
    return result


async def query_sql_db(user_input, db_instance):
    llm = ChatOpenAI(model_name=init.DEFAULT_CHAT_MODEL)
    toolkit = SQLDatabaseToolkit(db=db_instance, llm=llm)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True
    )
    result = await agent_executor.ainvoke(user_input)
    return result['output']

async def query_suria_sql_db(user_input):
    return await query_sql_db(user_input, db.suria_db)

async def query_sip_cde_sql_db(user_input):
    return await query_sql_db(user_input, db.sip_cde_db)

async def python_repl(
    code: Annotated[str, "The python code to execute to generate your chart."],
):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        # Set the matplotlib backend to 'Agg' to avoid issues with Tkinter
        matplotlib.use('Agg')

        # Remove any user-provided savefig or show statements
        modified_code = re.sub(r'plt\.savefig\(.*\)', '', code)
        modified_code = re.sub(r'plt\.show\(.*\)', '', modified_code)

        # Add code to save the image to a BytesIO object
        modified_code += (
            f"\nif 'plt' in globals() or 'plt' in locals():\n"
            f"    import io\n"
            f"    img_bytes = io.BytesIO()\n"
            f"    plt.savefig(img_bytes, format='png')\n"
            f"    img_bytes.seek(0)\n"
            f"    plt.close()\n"
            f"    import base64\n"
            f"    encoded_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')\n"
            f"    print(f'Image converted to bytes: {{encoded_image}}')"
        )

        result = repl.run(modified_code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"

    # Check if the result contains the encoded image
    if 'Image converted to bytes:' in result:
        try:
            # Extract the base64 encoded image from the result
            encoded_image = result.split('Image converted to bytes: ')[1].strip()

            # Decode the base64 string back to bytes
            img_bytes = io.BytesIO(base64.b64decode(encoded_image))

            # Now, upload to Google Cloud Storage
            link = await gcs.upload_and_download_file(
                cred_path=init.SURIA_DB_SERVICE_ACCOUNT_FILE,
                file_bytes=img_bytes,  # Pass the in-memory bytes directly
                file_extension='png',
                blob_name=f"{uuid.uuid4().hex}.png",
                bucket_name=init.GCS_BUCKET_NAME
            )
            return link
        except Exception as e:
            return "File is unsuccessfully uploaded or unable to be downloaded from google cloud: " + str(e)
    return "Error: Image is not created or converted to bytes"

# TOOLS
@tool
async def determine_db_to_query_tool(user_input: str):
    """
    Route all SQL database queries through this tool to determine the appropriate database.

    This tool serves as the entry point for any query related to the SQL databases. 
    It first utilizes an LLM to analyze the user's input and match it against existing vectors 
    in a MongoDB collection. This will then determine the appropriate database to be queried,
    and the result is returned.

    This tool should ALWAYS be invoked when the user's input involves querying a SQL database.
    It ensures that the correct database is selected before any actual data retrieval occurs.

    Args:
        user_input (str): The natural language query or input provided by the user.

    Returns:
        str: The result of the SQL query executed on either the "suria" or "sip-cde" database,
        or an error message if the LLM's output is unexpected.
    """
    temp = await determine_db_to_query(user_input)
    return temp
    
@tool
async def python_repl_tool(code):
    """
    Execute Python code and return the output.

    This tool allows you to execute a snippet of Python code. If the code produces
    output, it will be captured and returned as a string. If the execution fails, 
    an error message will be returned instead.

    Args:
        code (str): The Python code to execute. Ensure to use `print(...)` if you 
        want to see the output of any value.

    Returns:
        str: A message indicating the success or failure of the code execution. 
        If successful, the message will return a link in the form of a sring, which needs to sent
        to the user in full. If there is an error, the error message is returned.
    """
    temp = await python_repl(code)
    return temp