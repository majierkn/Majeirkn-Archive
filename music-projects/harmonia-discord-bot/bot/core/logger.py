import logging
import structlog

def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(processors=[structlog.stdlib.add_log_level, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()])

def get_logger(name: str):
    configure_logging(); return structlog.get_logger(name)
