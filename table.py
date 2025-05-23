from dataclasses import dataclass
from typing import List
from tabulate import tabulate
from logging_config import setup_logging

logger = setup_logging()

@dataclass
class Table:
    name: str
    headers: List[str]
    data: List[List[str]]
    current_row: int
    current_col: int

    def __init__(self, name: str, headers: List[str]):
        self.name = name
        self.headers = headers
        self.data = []
        self.current_row = 0
        self.current_col = 0
        self.new_row()
        logger.info(f"Создана таблица '{name}' с столбцами: {', '.join(headers)}")

    def new_row(self):
        """Добавляет новую строку в таблицу"""
        self.data.append(['_' for _ in range(len(self.headers))])
        logger.debug(f"Добавлена новая строка {self.current_row + 1}")

    def set_current_value(self, value: str, history_callback=None) -> bool:
        if self.current_col < len(self.headers):
            self.data[self.current_row][self.current_col] = value
            logger.info(f"Записано значение '{value}' в ячейку [строка {self.current_row + 1}, {self.headers[self.current_col]}]")
            self.current_col += 1
            if self.current_col >= len(self.headers):
                prev_row = self.current_row
                prev_col = self.current_col
                self.next_row()
                # Добавляем переход на новую строку в историю, если передан колбэк
                if history_callback:
                    history_callback(('next_row', prev_row, prev_col))
            return True
        return False

    def next_row(self) -> bool:
        self.current_row += 1
        self.current_col = 0
        self.new_row()
        logger.info(f"Переход к новой строке {self.current_row + 1}")
        return True

    def display(self):
        # Удаляем пустую последнюю строку при отображении
        display_data = self.data[:-1] if self.current_col == 0 else self.data
        print(f'\nТаблица "{self.name}":')
        print(tabulate(display_data, headers=self.headers, showindex=[f'Строка {i+1}' for i in range(len(display_data))]))
        print(f'\nТекущая позиция: Строка {self.current_row + 1}, {self.headers[self.current_col]}')
        print()

    def set_position(self, row: int, col: int) -> bool:
        """Устанавливает текущую позицию для редактирования"""
        if 0 <= row < len(self.data) and 0 <= col < len(self.headers):
            self.current_row = row
            self.current_col = col
            logger.info(f"Установлена позиция редактирования: строка {row + 1}, столбец {self.headers[col]}")
            return True
        return False
        
    def delete_row(self, row: int) -> bool:
        """Удаляет указанную строку из таблицы"""
        if 0 <= row < len(self.data) - 1:  # -1 чтобы не удалять последнюю пустую строку
            self.data.pop(row)
            if row < self.current_row:
                self.current_row -= 1
            return True
        return False

    def save_to_csv(self, filename: str = None):
        import csv
        if filename is None:
            filename = f'{self.name}.csv'
        # Сохраняем без пустой последней строки
        save_data = self.data[:-1] if self.current_col == 0 else self.data
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            writer.writerows(save_data)
        logger.info(f"Таблица сохранена в файл {filename}")