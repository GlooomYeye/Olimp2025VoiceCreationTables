import logging
import os
from datetime import datetime


def setup_logging(console_output=True):
    """
    Настраивает систему логирования.
    
    Args:
        console_output (bool): Флаг для включения/отключения вывода логов в консоль
    """
    # Создаём директорию для логов, если её нет
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Формируем имя лог-файла с текущей датой и временем
    log_filename = os.path.join(logs_dir, f'voice_table_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Настраиваем обработчики логов
    handlers = [logging.FileHandler(log_filename, encoding="utf-8")]
    if console_output:
        handlers.append(logging.StreamHandler())
    
    # Конфигурируем логгер
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    return logging.getLogger(__name__)
