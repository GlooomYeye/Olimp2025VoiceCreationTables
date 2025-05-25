import json
import logging
from typing import List, Optional
from datetime import datetime
import pyaudio
from vosk import Model, KaldiRecognizer
from text_to_num import alpha2digit
from table import Table
from logging_config import setup_logging
from constants import TEMPLATES


class VoiceTableCreator:
    def __init__(self):
        """Инициализация VoiceTableCreator с настройкой логирования, Vosk и PyAudio."""
        self.logger = logging.getLogger(__name__)
        setup_logging(console_output=False) 
        self.logger.info("Инициализация Voice Table Creator")

        # Инициализация модели распознавания речи
        self.model = Model("vosk-model-small-ru-0.22")
        self.table: Optional[Table] = None
        self.history = []

        # Инициализация PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        self.rec = KaldiRecognizer(self.model, 16000)
        self.last_filled_position = None
        self.logger.info("Voice Table Creator успешно инициализирован")

    def __del__(self):
        """Освобождение ресурсов PyAudio при уничтожении объекта."""
        self.logger.info("Завершение работы Voice Table Creator")
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

    def text_to_number(self, text: str) -> float:
        """Преобразует текст числа в числовое значение с помощью text_to_num."""
        text = text.strip().lower()
        if not text:
            raise ValueError("Пустой текст для конвертации в число")

        try:
            number = alpha2digit(text, "ru")
            self.logger.debug(f"Преобразовано '{text}' в число {number}")
            return float(number)
        except ValueError as e:
            self.logger.error(f"Не удалось преобразовать '{text}' в число: {str(e)}")
            raise ValueError(f"Не удалось преобразовать '{text}' в число")

    def words_to_number(self, text: str) -> str:
        """Преобразует текст, содержащий числа, в строку с числовыми значениями."""
        try:
            number = self.text_to_number(text)
            return str(number).replace(".", ",")
        except ValueError:
            return text

    def listen_command(self, show_listening: bool = True) -> str:
        """Слушает голосовую команду и возвращает распознанный текст."""
        if show_listening:
            print("\nСлушаю...")
        self.rec.Reset()
        while True:
            data = self.stream.read(4000, exception_on_overflow=False)
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                text = result.get("text", "").strip()
                if text:
                    self.logger.info(f"Распознано: '{text}'")
                    return text
        return ""

    def create_from_template(self, template_name: str) -> bool:
        """Создаёт таблицу из шаблона."""
        template = TEMPLATES.get(template_name.lower())
        if not template:
            self.logger.warning(f"Шаблон '{template_name}' не найден")
            print(f"Шаблон '{template_name}' не найден. Доступные шаблоны: {', '.join(TEMPLATES.keys())}")
            return False

        self.create_table(template["name"], template["headers"])
        self.logger.info(f"Создана таблица из шаблона: {template_name}")
        return True

    def extract_table_info(self, command: str) -> tuple[str, List[str]]:
        """Извлекает название таблицы и заголовки столбцов из команды."""
        words = command.lower().split()
        try:
            table_idx = words.index("таблицу") + 1
            columns_idx = words.index("столбцы") + 1
            if table_idx < columns_idx and table_idx < len(words):
                table_name = " ".join(words[table_idx : columns_idx - 1])
                headers = words[columns_idx:]
                self.logger.debug(f"Извлечено: таблица '{table_name}', столбцы {headers}")
                return table_name, headers
        except ValueError:
            self.logger.warning(f"Некорректная команда для создания таблицы: {command}")
        return "", []

    def extract_number(self, command: str, after_word: str) -> Optional[int]:
        """Извлекает число после указанного слова в команде."""
        words = command.lower().split()
        try:
            idx = words.index(after_word) + 1
            if idx < len(words):
                return int(self.text_to_number(words[idx]))
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Не удалось извлечь число после '{after_word}' в команде '{command}': {str(e)}")
        return None

    def create_table(self, name: str, headers: List[str]):
        """Создаёт новую таблицу с указанным именем и заголовками."""
        prev_table = self.table
        self.table = Table(name, headers, console_output=False) 
        self.history.append(("create", prev_table))
        print(f"\nСоздана таблица '{name}' со следующими столбцами:")
        print(", ".join(headers))
        self.table.display()

    def set_value(self, value: str) -> bool:
        """Устанавливает значение в текущую ячейку таблицы."""
        if not self.table:
            self.logger.warning("Попытка записи значения без созданной таблицы")
            print("Сначала создайте таблицу")
            return False

        if self.table.current_col >= len(self.table.headers):
            self.logger.info("Достигнут конец строки, автоматический переход на следующую")
            print("Достигнут конец строки. Автоматически перехожу на следующую строку")
            self.next_row()
            return False

        value_converted = self.words_to_number(value)
        prev_row = self.table.current_row
        prev_col = self.table.current_col
        prev_value = self.table.data[prev_row][prev_col]

        if self.table.set_current_value(value_converted, history_callback=lambda action: self.history.append(action)):
            self.history.append(("set", prev_row, prev_col, prev_value))
            self.table.display()
            return True
        return False

    def next_row(self):
        """Переходит на следующую строку таблицы."""
        if not self.table:
            self.logger.warning("Попытка перехода на следующую строку без созданной таблицы")
            print("Сначала создайте таблицу")
            return

        prev_row = self.table.current_row
        prev_col = self.table.current_col
        if self.table.next_row():
            self.history.append(("next_row", prev_row, prev_col))
            self.table.display()

    def skip_cell(self):
        """Пропускает текущую ячейку, устанавливая значение '_'."""
        if not self.table:
            self.logger.warning("Попытка пропуска ячейки без созданной таблицы")
            print("Сначала создайте таблицу")
            return

        if self.table.current_col < len(self.table.headers):
            self.set_value("_")
            self.logger.info(
                f"Пропущена ячейка [строка {self.table.current_row + 1}, {self.table.headers[self.table.current_col]}]"
            )

    def undo_last_action(self):
        """Отменяет последнее действие."""
        if not self.history:
            self.logger.info("Попытка отмены действия при пустой истории")
            print("Нечего отменять")
            return

        action = self.history.pop()
        self.logger.info(f"Отмена действия: {action[0]}")

        if action[0] == "create":
            self.table = action[1]
        elif action[0] == "set":
            row, col, prev_value = action[1], action[2], action[3]
            self.table.data[row][col] = prev_value
            self.table.current_row = row
            self.table.current_col = col
            self.logger.info(
                f"Восстановлено значение '{prev_value}' в ячейку [строка {row + 1}, {self.table.headers[col]}]"
            )
        elif action[0] == "next_row":
            prev_row, prev_col = action[1], action[2]
            self.table.current_row = prev_row
            self.table.current_col = prev_col
            # Удаляем последнюю пустую строку, если она существует и не нужна
            if len(self.table.data) > prev_row + 1 and all(val == "_" for val in self.table.data[-1]):
                self.table.data.pop()
            self.logger.info(f"Возврат к строке {prev_row + 1}")
        elif action[0] == "delete_row":
            row, row_data = action[1], action[2]
            self.table.data.insert(row, row_data)
            if row <= self.table.current_row:
                self.table.current_row += 1
            self.logger.info(f"Восстановлена удаленная строка {row + 1}")

        elif action[0] == "insert_row":
            row = action[1]
            self.table.data.pop(row)
            if row < self.table.current_row:
                self.table.current_row -= 1
            self.logger.info(f"Удалена вставленная строка {row + 1}")

        if self.table:

            if (
                self.table.current_col == 0
                and len(self.table.data) > self.table.current_row + 1
                and all(val == "_" for val in self.table.data[self.table.current_row])
            ):
                self.table.data.pop()
                self.table.current_row -= 1
            self.table.display()

    def print_help(self):
        """Выводит список доступных команд."""
        print("\nДоступные команды:")
        print("- создай таблицу [название] столбцы [названия столбцов]")
        print("- создай таблицу шаблон [номер] (доступные шаблоны: 1, 2, 3)")
        print("- следующая строка")
        print("- отмена")
        print("- пропусти (пропуск текущей ячейки)")
        print("- сохрани")
        print("- выход")
        print("- редактировать строка [номер] столбец [название]")
        print("- удалить строка [номер]")
        print("- вставить строка [номер]")
        print("- вернуться")
        print("- помощь (показать этот список)")
        print("\nПросто произносите значения для заполнения текущей ячейки")

    def run(self):
        """Запускает основной цикл обработки голосовых команд."""
        self.logger.info("Запуск Voice Table Creator")
        print("Голосовой создатель таблиц запущен!")
        self.print_help()

        while True:
            command = self.listen_command().lower()
            if not command:
                continue

            print(f"Распознано: {command}")

            if "пауза" in command:
                print("Пауза. Для продолжения скажите 'продолжить'.")
                self.logger.info("Вход в режим паузы")
                while True:
                    pause_cmd = self.listen_command(show_listening=False).lower()
                    if "продолжить" in pause_cmd or "продолжай" in pause_cmd:
                        print("Продолжаю заполнение таблицы.")
                        self.logger.info("Выход из режима паузы")
                        if self.table:
                            self.table.display()
                        break

            elif "выход" in command:
                self.logger.info("Получена команда выхода")
                break

            elif "помощь" in command:
                self.print_help()

            elif "создай таблицу шаблон" in command or "создать таблицу шаблон" in command:
                template_num = self.extract_number(command, "шаблон")
                if template_num is not None and 1 <= template_num <= 3:
                    self.create_from_template(f"шаблон {template_num}")
                else:
                    print("Неверный номер шаблона. Доступные шаблоны: 1, 2, 3")

            elif "создай таблицу" in command or "создать таблицу" in command:
                name, headers = self.extract_table_info(command)
                if name and headers:
                    self.create_table(name, headers)
                else:
                    print("Не удалось распознать название таблицы или столбцы.")
                    print("Пример команды: создай таблицу турнир столбцы фамилия имя команда балл")
                    print("Или используйте шаблон: создай таблицу шаблон 1")

            elif "следующая строка" in command:
                self.next_row()

            elif "пропусти" in command or "пропуск" in command:
                self.skip_cell()

            elif "отмена" in command:
                self.undo_last_action()

            elif "вставь строка" in command or "вставить строка" in command:
                row_num = self.extract_number(command, "строка")
                if row_num is None:
                    print("Не удалось распознать номер строки")
                    continue

                if self.table and 1 <= row_num <= len(self.table.data) + 1:
                    if self.table.insert_row(row_num - 1):
                        self.history.append(("insert_row", row_num - 1))
                        print(f"Вставлена новая строка перед строкой {row_num}")
                        self.table.display()
                else:
                    print(f"Неверный номер строки (должен быть от 1 до {len(self.table.data) + 1})")

            elif "сохрани" in command:
                if self.table:
                    filename = f"{self.table.name}.csv"
                    self.table.save_to_csv()
                    print(f"Таблица сохранена в файл {filename}")
                    self.table = None
                    print("\nМожете создать новую таблицу")
                else:
                    print("Нет таблицы для сохранения")

            elif "редактировать" in command:
                row_num = self.extract_number(command, "строка")
                if row_num is None:
                    print("Не удалось распознать номер строки")
                    continue

                words = command.split()
                try:
                    col_idx = words.index("столбец") + 1
                    if col_idx < len(words) and self.table:
                        col_name = words[col_idx]
                        try:
                            col = self.table.headers.index(col_name)
                            if self.table.set_position(row_num - 1, col):
                                print(f"\nРедактирование ячейки: строка {row_num}, {col_name}")
                                print("Произнесите новое значение")
                                self.table.display()
                                # Ожидаем новое значение
                                new_value = self.listen_command()
                                if new_value:
                                    prev_value = self.table.data[row_num - 1][col]
                                    self.table.set_current_value(
                                        self.words_to_number(new_value),
                                        history_callback=lambda action: self.history.append(action),
                                    )
                                    self.history.append(("set", row_num - 1, col, prev_value))
                                    self.table.display()
                            else:
                                print(f"Невозможно редактировать: неверная позиция")
                        except ValueError:
                            print(f"Столбец '{col_name}' не найден")
                    else:
                        print("Неверный формат команды редактирования")
                except ValueError:
                    print("Неверный формат команды редактирования")

            elif "вернуться" in command or "назад" in command or "вернись" in command:
                if self.table and self.table.previous_position:
                    row, col = self.table.previous_position
                    if self.table.set_position(row, col):
                        print(f"↩ Возврат к позиции: строка {row+1}, {self.table.headers[col]}")
                        self.table.display()
                    else:
                        print("Ошибка: неверная позиция для возврата")
                else:
                    print("Нет сохранённой позиции для возврата")

            elif "удалить строка" in command:
                row_num = self.extract_number(command, "строка")
                if row_num is None:
                    print("Не удалось распознать номер строки")
                    continue

                if self.table and 1 <= row_num <= len(self.table.data):
                    row_data = self.table.data[row_num - 1].copy()
                    if self.table.delete_row(row_num - 1):
                        self.history.append(("delete_row", row_num - 1, row_data))
                        print(f"Строка {row_num} удалена")
                        self.table.display()
                else:
                    print(f"Неверный номер строки или таблица пуста")

            else:
                self.set_value(command)
