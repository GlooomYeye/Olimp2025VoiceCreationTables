import logging
import os
from datetime import datetime


def setup_logging(console_output=True):

    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = os.path.join(logs_dir, f'voice_table_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    handlers = [logging.FileHandler(log_filename, encoding="utf-8")]
    if console_output:
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    return logging.getLogger(__name__)
