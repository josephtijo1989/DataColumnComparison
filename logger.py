import logging
import os
import sys
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")

# Configure logger format with precise timestamp
logger = logging.getLogger("DataColumnComparison")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    fmt="[%(asctime)s.%(msec)03d] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# File Handler
file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_step(step_name: str, message: str, level: str = "info"):
    msg = f"[{step_name}] {message}"
    if level.lower() == "error":
        logger.error(msg, exc_info=True)
    elif level.lower() == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)
