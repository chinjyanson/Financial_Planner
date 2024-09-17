from langchain_community.utilities import SQLDatabase
from google.cloud.sql.connector import Connector
import sqlalchemy
from . import initializer as init

from google.oauth2 import service_account

# Function to initialize connector with a specific credential
def create_connector(credential_path):
    # os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
    credentials = service_account.Credentials.from_service_account_file(credential_path)
    connector = Connector(credentials=credentials)
    return connector

# Load the credential set
# connector_1 = create_connector(os.getenv('GOOGLE_APPLICATION_CREDENTIALS_1'))
# connector_2 = create_connector(os.getenv('GOOGLE_APPLICATION_CREDENTIALS_2'))
# for suria
connector_1 = create_connector(init.SURIA_DB_SERVICE_ACCOUNT_FILE)
# for sip-cde
connector_2 = create_connector(init.SIP_CDE_DB_SERVICE_ACCOUNT_FILE)

def getconn(connector: Connector, instance_name, user, db):
    conn = connector.connect(
      instance_name,
      "pg8000",
      user=user,
      db=db,
      enable_iam_auth=True
    )
    return conn

# getconn now using IAM user and requiring no password with IAM Auth enabled
def getconn_1():
    return getconn(connector_1, init.INSTANCE_CONNECTION_NAME_1, init.IAM_USER_1, init.DB_NAME_1)

def getconn_2():
    return getconn(connector_2, init.INSTANCE_CONNECTION_NAME_2, init.IAM_USER_2, init.DB_NAME_2)
 
connectors = [getconn_1(), getconn_2()]
# create connection pool
pools = [(sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=lambda conn=connector: conn  ,
)) for connector in connectors]

# connect to connection pool
for pool in pools:
    print(type(pool))
    with pool.connect() as db_conn:
        # get current datetime from database
        results = db_conn.execute(sqlalchemy.text("SELECT NOW()")).fetchone()

        # output time
        print("Current time: ", results[0])

suria_db = SQLDatabase(engine=pools[0])
sip_cde_db = SQLDatabase(engine=pools[1])
 
# cleanup connector
connector_1.close()
connector_2.close()