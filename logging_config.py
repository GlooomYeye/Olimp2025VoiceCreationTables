import logging
import os
from datetime import datetime


def setup_logging():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = os.path.join(logs_dir, f'voice_table_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger(__name__)
