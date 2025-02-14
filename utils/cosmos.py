import os
import azure.cosmos.cosmos_client as cosmos_client

# initialize CosmosDB
client_ = cosmos_client.CosmosClient(
    os.getenv("COSMOS_URL"),
    {"masterKey": os.getenv("COSMOS_KEY")},
    user_agent="qfa-api",
    user_agent_overwrite=True,
)
cosmos_db = client_.get_database_client("qfa")
cosmos_container_client = cosmos_db.get_container_client("qfa-schema")
