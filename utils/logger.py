import logging
import os
from fastapi import HTTPException
from dotenv import load_dotenv
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter

# load environment variables
load_dotenv()

# Set up logs export to Azure Application Insights
logger_provider = LoggerProvider()
set_logger_provider(logger_provider)
exporter = AzureMonitorLogExporter(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

# Attach LoggingHandler to root logger
handler = LoggingHandler()
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.NOTSET)
logger = logging.getLogger(__name__)

# Silence noisy loggers
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("filelock").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def raise_and_log(status_code: int, detail: str = "", extra_logs: dict = None):
    """
    Raise an HTTPException and log the error.
    Args:
        status_code (int): HTTP status code.
        detail (str): Error message to log.
        extra_logs (dict): Additional information to log.
    """
    logger.error(
        detail,
        extra=extra_logs,
    )
    raise HTTPException(
        status_code=status_code,
        detail=detail,
    )
