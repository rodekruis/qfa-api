import os
import azure.cosmos.cosmos_client as cosmos_client
from utils.sources import Source
from urllib.parse import urlparse


# initialize CosmosDB
client_ = cosmos_client.CosmosClient(
    os.getenv("COSMOS_URL"),
    {"masterKey": os.getenv("COSMOS_KEY")},
    user_agent="qfa-api",
    user_agent_overwrite=True,
)
cosmos_db = client_.get_database_client("qfa")
cosmos_container_client = cosmos_db.get_container_client("qfa-schema")


def cosmos_source_id(source: Source, source_origin: str) -> str:
    if source != Source.KOBO:
        source_id = urlparse(source_origin).netloc
    else:
        source_id = source_origin
    return source_id
