import re
import pandas as pd
import uvicorn
import base64
import io
import os
from functools import wraps
from fastapi import FastAPI, HTTPException, Response, Request, UploadFile, File, Query, Depends, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_users.exceptions import UserInactive, InvalidVerifyToken

from fastapi.middleware.cors import CORSMiddleware
from components import initializer as init
import tools.ocr as ocr_tools
import components.initializer as init
from components.conversation_handler import handle_single_agent_all

# Initialize FastAPI 
from beanie import init_beanie
from fastapi import Depends, FastAPI
from contextlib import asynccontextmanager
from users.db import User
from users.schemas import UserCreate, UserRead, UserUpdate
from users.users import auth_backend, current_active_user, fastapi_users

# Initialise beanie for user management 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_beanie(
        database=init.mongodb,  
        document_models=[
            User,  
        ],
    )
    yield

app = FastAPI(lifespan=lifespan)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


"""
For permission:
new = new chat
no permission = no permission needed to be asked
ask permission = need permission
finish = finish
"""
# Status should be retrieved from a document on mongodb per thread id 
# thread id is associated with a user id 

@app.get("/upload-atlas-vectors")
async def upload_vectors():
    # Replace the following line with the path to your own text file
    # with open(init.SIP_CDE_SUMMARY_PATH, "r") as file:
    #     faq_text = file.read()

    with open(init.SURIA_SUMMARY_PATH, "r") as file:
        faq_text = file.read()

    # Split the text into sections (to split the texts, use ##, this create a new document for each section)
    df = pd.DataFrame([txt for txt in re.split(r"(?=\n##)", faq_text)], columns=["page_content"])
    
    # Add a column for the database name
    df['database_name'] = 'suria'  # Replace with the actual database name

    # Generate embeddings using your OpenAI client
    res = init.openai_client.embeddings.create(input=df['page_content'], model=init.DEFAULT_EMBEDDINGS_MODEL)
    embeddings = [data.embedding for data in res.data]
    df['embeddings'] = embeddings
    
    # Convert the DataFrame to a list of dictionaries
    df_dict = df.to_dict(orient="records")

    # Insert the data into MongoDB
    collection = init.mongodb.get_collection("sql_db_description")
    collection.insert_many(df_dict)

    return {
        "message": "Vectors uploaded successfully",
    }


def add_padding(encoded_string):
    # Add padding to make the length a multiple of 4
    return encoded_string + '=' * (-len(encoded_string) % 4)

"""
Single-agent chatbot
"""
@app.post("/single_agent_with_response/")
async def single_agent_response(question: str = Form(..., description="Enter the question"), file : UploadFile = File(None,description="Attach a file to use OCR services"), user=Depends(current_active_user)):
    try:
        message = await handle_single_agent_all(question, str(user.thread_id[0]), file)
        return Response(content=message, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def authenticate_user(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    user_pass = f"{credentials.username}:{credentials.password}"
    user_pass_encode = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")
    server_pass = f"{init.OCR_API_KEY}:{init.OCR_API_SECRET}"
    server_pass_encode = base64.b64encode(server_pass.encode("utf-8")).decode("utf-8")
    return user_pass_encode == server_pass_encode

# decorator that calls authenticate_user (which returns a boolean) and if it returns False, it will return a 401 status code
def check_authentication(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        credentials = kwargs.get("credentials")
        if not authenticate_user(credentials):
            return {"message": "Unauthorized","status":401}
        return await func(*args, **kwargs)
    return wrapper

@app.post("/use_ocr_service", summary="Get response from Gemini", description="You must put the PDF file. You can either put the list of fields to extract (string of fields separated by commas) or the prompt. If you put both, the user prompt that you passed will be prioritised. The response will be returned in a JSON format.", tags=["Get Response"])
@check_authentication
async def use_ocr_service(file : UploadFile =File(..., description="The PDF file to upload"), list_to_extract: str = Query(None, description="Comma-separated list of fields to extract from the PDF."), user_prompt: str = Query(None, description="Feel free to pass your own prompt. Note if you enter both parameters, the user prompt will get prioritised."), credentials: HTTPBasicCredentials = Depends(HTTPBasic())): 
    # try to open the file and convert to base64
    try:
        contents = file.file.read()
        file_bytes = io.BytesIO(contents)
        file_extension = os.path.splitext(file.filename)[1]
        if file_extension not in [".pdf", ".jpeg", ".jpg", ".png"]:
            return {'message':f'Please attach a PDF/JPEG/JPG or PNG file. You have attached a {file_extension} file.','status': 400}
        
        if not ocr_tools.validate_file(file_bytes, file_extension):
            return {'message':'File failed to be accessed. Please upload a different file.','status': 400}
        file_base64 = base64.b64encode(file_bytes.getvalue()).decode('utf-8')
    except Exception as e:
        return {'message':'Please attach a PDF first before accessing our OCR service.','status': 400}
    finally:
        file.file.close()
    response_dict = ocr_tools.generate(file_base64,file_extension.replace('.',''),list_to_extract, user_prompt)
    if response_dict['status'] == 400:
        return {'message':'Response not generated. Please check your prompt again.' + str(response_dict['message']),'status': 400}
    return {'message':'Response generated','response': response_dict['response'], 'status': 200}
    


def fastapi_main():
    uvicorn.run("components.routes:app", host="127.0.0.1", port=8000, workers=4)