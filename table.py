from dataclasses import dataclass
from typing import List, Optional
from tabulate import tabulate
import logging
from logging_config import setup_logging

@dataclass
class Table:
    name: str
    headers: List[str]
    data: List[List[str]] = None
    current_row: int = 0
    current_col: int = 0
    logger: logging.Logger = None
    previous_position: Optional[tuple] = None

    def __init__(self, name: str, headers: List[str], console_output: bool = False):
        self.name = name
        self.headers = headers
        self.data = []
        self.current_row = 0
        self.current_col = 0
        self.previous_position = None
        self.logger = setup_logging(console_output=console_output)
        self.new_row()
        self.logger.info(f"Создана таблица '{name}' с столбцами: {', '.join(headers)}")

    def new_row(self):
        """Добавляет новую строку в таблицу"""
        self.data.append(["_" for _ in range(len(self.headers))])
        self.logger.debug(f"Добавлена новая строка {self.current_row + 1}")

    def set_current_value(self, value: str, history_callback=None) -> bool:
        if self.current_col < len(self.headers):
            self.data[self.current_row][self.current_col] = value
            self.logger.info(
                f"Записано значение '{value}' в ячейку [строка {self.current_row + 1}, {self.headers[self.current_col]}]"
            )
            if value != "_":
                self.last_filled_position = (self.current_row, self.current_col)
            self.current_col += 1
            if self.current_col >= len(self.headers):
                prev_row = self.current_row
                prev_col = self.current_col
                self.next_row()
                if history_callback:
                    history_callback(("next_row", prev_row, prev_col))
            return True
        return False

    def next_row(self) -> bool:
        self.current_row += 1
        self.current_col = 0
        self.new_row()
        self.logger.info(f"Переход к новой строке {self.current_row + 1}")
        return True

    def display(self):
        display_data = self.data
        if self.current_col == 0 and len(self.data) > self.current_row + 1 and all(val == "_" for val in self.data[-1]):
            display_data = self.data[:-1]
        print(f'\nТаблица "{self.name}":')
        print(
            tabulate(display_data, headers=self.headers, showindex=[f"Строка {i+1}" for i in range(len(display_data))])
        )
        print(f"\nТекущая позиция: Строка {self.current_row + 1}, {self.headers[self.current_col]}")
        print()

    def set_position(self, row: int, col: int) -> bool:
        """Устанавливает текущую позицию для редактирования"""
        if 0 <= row < len(self.data) and 0 <= col < len(self.headers):
            self.previous_position = (self.current_row, self.current_col)
            self.current_row = row
            self.current_col = col
            self.logger.info(f"Установлена позиция: строка {row+1}, столбец {self.headers[col]}")
            return True
        return False

    def delete_row(self, row: int) -> bool:
        """Удаляет указанную строку из таблицы"""
        if 0 <= row < len(self.data):
            self.data.pop(row)
            if row < self.current_row:
                self.current_row -= 1
            if not self.data:
                self.new_row()
            self.logger.info(f"Удалена строка {row + 1}")
            return True
        self.logger.warning(f"Неверный индекс строки {row} для удаления")
        return False

    def insert_row(self, row: int) -> bool:
        """Вставляет новую строку перед указанной позицией"""
        if 0 <= row <= len(self.data):
            self.data.insert(row, ["_" for _ in range(len(self.headers))])

            if row <= self.current_row:
                self.current_row += 1

            self.logger.info(f"Вставлена новая строка перед позицией {row + 1}")
            return True
        self.logger.warning(f"Неверный индекс строки {row} для вставки")
        return False

    def save_to_csv(self, filename: str = None):
        import csv

        if filename is None:
            filename = f"{self.name}.csv"
        save_data = self.data[:-1] if self.current_col == 0 else self.data
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            writer.writerows(save_data)
        self.logger.info(f"Таблица сохранена в файл {filename}")
