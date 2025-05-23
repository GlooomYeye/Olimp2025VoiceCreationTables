import json
import csv
import pyaudio
from vosk import Model, KaldiRecognizer
from typing import List, Optional
from datetime import datetime
import logging
from table import Table
from logging_config import setup_logging
from constants import NUMBER_WORDS

class VoiceTableCreator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        setup_logging() 
        self.logger.info("Инициализация Voice Table Creator")
        
        # Инициализация модели распознавания речи
        self.model = Model("vosk-model-small-ru-0.22")
        self.table: Optional[Table] = None
        self.history = []
        
        # Инициализация PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000
        )
        
        self.rec = KaldiRecognizer(self.model, 16000)
        self.logger.info("Voice Table Creator успешно инициализирован")

    def listen_command(self) -> str:
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

    def extract_table_info(self, command: str) -> tuple[str, List[str]]:
        # Разделяем команду на слова
        words = command.split()
        # Ищем название таблицы после слова "таблицу" и столбцы после слова "столбцы"
        table_name = ""
        headers = []
        
        try:
            table_idx = words.index("таблицу") + 1
            columns_idx = words.index("столбцы") + 1
            
            if table_idx < columns_idx and table_idx < len(words):
                table_name = " ".join(words[table_idx:columns_idx-1])
                headers = words[columns_idx:]
                
                self.logger.debug(f"Извлечено название таблицы: {table_name}")
                self.logger.debug(f"Извлечены заголовки столбцов: {headers}")
                
                return table_name, headers
        except ValueError:
            pass
        
        return "", []

    def words_to_number(self, text: str) -> str:
        """Преобразует слова в числа в тексте"""
        words = text.lower().split()
        result = []
        i = 0
        n = len(words)
        
        def get_full_number() -> tuple[float, int]:
            """Получает полное число из последовательности слов"""
            nonlocal i
            num = 0
            start_i = i

            while i < n and words[i] in NUMBER_WORDS:
                # Обработка "полтора" и "полторы"
                if words[i] in ("полтора", "полторы"):
                    num += 1.5
                    i += 1
                    break
                curr_num = float(NUMBER_WORDS[words[i]])
                # Если десятки и за ними единицы (например, "двадцать восемь")
                if curr_num in (20, 30, 40, 50, 60, 70, 80, 90) and i + 1 < n and words[i+1] in NUMBER_WORDS and 1 <= float(NUMBER_WORDS[words[i+1]]) <= 9:
                    curr_num += float(NUMBER_WORDS[words[i+1]])
                    i += 1
                num += curr_num
                i += 1

            # Если ничего не набрали, вернуть хотя бы первое слово
            if num == 0:
                num = float(NUMBER_WORDS[words[start_i]])
            return num, i
        
        while i < n:
            word = words[i]

            # Обработка "полтора" и "полторы" как отдельного случая
            if word in ("полтора", "полторы"):
                result.append("1,5")
                i += 1
                continue

            # Обработка паттерна: [целая часть] и/целых/целая [дробная часть]
            if word in NUMBER_WORDS:
                # Проверяем наличие десятичной части
                if i + 1 < n and words[i + 1] in ['целых', 'целая', 'и']:
                    whole_num, new_i = get_full_number()
                    i = new_i
                    
                    # Пропускаем слова "целых"/"целая"/"и"
                    if i < n and words[i] in ['целых', 'целая', 'и']:
                        i += 1
                    
                    # Получаем десятичную часть
                    if i < n and words[i] in NUMBER_WORDS:
                        decimal_num, new_i = get_full_number()
                        i = new_i

                        # Определяем разрядность десятичной части
                        decimal_places = 1
                        if i < n:
                            if words[i] == 'десятых':
                                decimal_places = 1
                            elif words[i] == 'сотых':
                                decimal_places = 2
                            elif words[i] == 'тысячных':
                                decimal_places = 3
                            i += 1

                        # Формируем десятичное число
                        decimal_str = str(int(decimal_num)).zfill(decimal_places)
                        result.append(f"{int(whole_num)},{decimal_str}")
                        continue

                # Обработка паттерна: число и число (например, "4 и 3" -> "4,3")
                if i + 2 < n and words[i+1] == "и" and words[i+2] in NUMBER_WORDS:
                    left = NUMBER_WORDS[words[i]]
                    right = NUMBER_WORDS[words[i+2]]
                    result.append(f"{left},{right}")  # Используем запятую как разделитель для десятичной части
                    i += 3
                    continue
                # Обычные целые числа
                num, new_i = get_full_number()
                # i уже обновлен внутри get_full_number
                result.append(str(int(num)))
                continue # Пропускаем оставшуюся часть цикла
            elif word.replace('.', '').replace(',', '').isdigit():
                # Если это уже число, используем запятую как разделитель
                result.append(word.replace('.', ','))
            else:
                # Оставляем слово как есть
                result.append(word)
                i += 1
        
        return ' '.join(result)
    
    def listen_command(self) -> str:
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
    
    def extract_table_info(self, command: str) -> tuple[str, List[str]]:
        # Разделяем команду на слова
        words = command.split()
        
        # Ищем название таблицы после слова "таблицу" и столбцы после слова "столбцы"
        table_name = ""
        headers = []
        
        try:
            table_idx = words.index("таблицу") + 1
            columns_idx = words.index("столбцы") + 1
            
            if table_idx < columns_idx and table_idx < len(words):
                table_name = " ".join(words[table_idx:columns_idx-1])
                headers = words[columns_idx:]
                
                self.logger.debug(f"Извлечено название таблицы: {table_name}")
                self.logger.debug(f"Извлечены заголовки столбцов: {headers}")
                
                return table_name, headers
        except ValueError:
            pass
        
        return "", []


    def create_table(self, name: str, headers: List[str]):
        prev_table = self.table
        self.table = Table(name, headers)
        self.history.append(('create', prev_table))
        print(f"\nСоздана таблица '{name}' со следующими столбцами:")
        print(", ".join(headers))
        self.table.display()

    def set_value(self, value: str):
        if not self.table:
            self.logger.warning("Попытка записи значения без созданной таблицы")
            print("Сначала создайте таблицу")
            return False

        if self.table.current_col >= len(self.table.headers):
            self.logger.info("Достигнут конец строки, автоматический переход на следующую")
            print("Достигнут конец строки. Автоматически перехожу на следующую строку")
            return False

        # Преобразуем слова в числа
        value_converted = self.words_to_number(value)

        prev_row = self.table.current_row
        prev_col = self.table.current_col
        prev_value = self.table.data[self.table.current_row][self.table.current_col]

        def add_history(action):
            self.history.append(action)

        if self.table.set_current_value(value_converted, history_callback=add_history):
            self.history.append(('set', prev_row, prev_col, prev_value))
            self.table.display()
            return True
        return False

    def next_row(self):
        if not self.table:
            self.logger.warning("Попытка перехода на следующую строку без созданной таблицы")
            print("Сначала создайте таблицу")
            return
            
        prev_row = self.table.current_row
        prev_col = self.table.current_col
        if self.table.next_row():
            self.history.append(('next_row', prev_row, prev_col))
            self.table.display()

    def skip_cell(self):
        if not self.table:
            self.logger.warning("Попытка пропуска ячейки без созданной таблицы")
            print("Сначала создайте таблицу")
            return
            
        if self.table.current_col < len(self.table.headers):
            self.set_value("_")
            self.logger.info(f"Пропущена ячейка [строка {self.table.current_row}, {self.table.headers[self.table.current_col]}]")

    def undo_last_action(self):
        if not self.history:
            self.logger.info("Попытка отмены действия при пустой истории")
            print("Нечего отменять")
            return

        action = self.history.pop()
        self.logger.info(f"Отмена последнего действия: {action[0]}")
        
        if action[0] == 'create':
            # Восстанавливаем предыдущую таблицу
            self.table = action[1]
        elif action[0] == 'set':
            # Восстанавливаем предыдущее значение ячейки
            row, col, prev_value = action[1], action[2], action[3]
            self.table.data[row][col] = prev_value
            self.table.current_row = row
            self.table.current_col = col
            self.logger.info(f"Возврат значения '{prev_value}' в ячейку [строка {row + 1}, {self.table.headers[col]}]")
        elif action[0] == 'next_row':
            # Отменяем переход на следующую строку
            prev_row, prev_col = action[1], action[2]
            self.table.current_row = prev_row
            self.table.current_col = prev_col
            if len(self.table.data) > prev_row + 1:
                self.table.data.pop()
            self.logger.info(f"Возврат к строке {prev_row + 1}")
        elif action[0] == 'delete_row':
            # Восстанавливаем удаленную строку
            row, row_data = action[1], action[2]
            self.table.data.insert(row, row_data)
            if row <= self.table.current_row:
                self.table.current_row += 1
            self.logger.info(f"Восстановлена удаленная строка {row + 1}")

        if self.table:
            self.table.display()

    def run(self):
        self.logger.info("Запуск Voice Table Creator")
        print("Голосовой создатель таблиц запущен!")
        print("\nДоступные команды:")
        print('- создай таблицу [название] столбцы [названия столбцов]')
        print("- следующая строка")
        print("- отмена")
        print("- пропусти (пропуск текущей ячейки)")
        print("- сохрани")
        print("- выход")
        print("- редактировать строка [номер] столбец [название]")
        print("- удалить строка [номер]")
        print("\nПросто произносите значения для заполнения текущей ячейки")
        
        while True:
            command = self.listen_command().lower()
            print(f"Распознано: {command}")

            if "пауза" in command:
                print("Пауза. Для продолжения скажите 'продолжить'.")
                self.logger.info("Вход в режим паузы")
                while True:
                    pause_cmd = self.listen_command().lower()
                    print(f"Распознано (пауза): {pause_cmd}")
                    if "продолжить" in pause_cmd or "продолжай" in pause_cmd:
                        print("Продолжаю заполнение таблицы.")
                        self.logger.info("Выход из режима паузы")
                        break

            elif "выход" in command:
                self.logger.info("Получена команда выхода")
                break

            elif "создай таблицу" in command or "создать таблицу" in command:
                name, headers = self.extract_table_info(command)
                if name and headers:
                    self.logger.info(f"Создание таблицы '{name}' с столбцами: {headers}")
                    self.create_table(name, headers)
                else:
                    self.logger.warning("Не удалось распознать название таблицы или столбцы")
                    print("Не удалось распознать название таблицы или столбцы.")
                    print("Пример команды:")
                    print("- создай таблицу турнир столбцы фамилия имя команда балл")

            elif "следующая строка" in command:
                self.logger.info("Получена команда перехода на следующую строку")
                self.next_row()

            elif "пропусти" in command or "пропуск" in command:
                self.logger.info("Получена команда пропуска текущей ячейки")
                self.skip_cell()

            elif "отмена" in command:
                self.logger.info("Получена команда отмены")
                self.undo_last_action()

            elif "сохрани" in command:
                self.logger.info("Получена команда сохранения")
                if self.table:
                    filename = f'{self.table.name}.csv'
                    self.table.save_to_csv()
                    print(f'Таблица сохранена в файл {filename}')
                    self.table = None
                    print("\nМожете создать новую таблицу")

            elif "редактировать" in command:
                # Извлекаем номер строки и название столбца
                words = command.split()
                try:
                    row_idx = words.index("строка") + 1
                    col_idx = words.index("столбец") + 1

                    if row_idx < len(words) and col_idx < len(words):
                        row = int(words[row_idx]) - 1  # Преобразуем в 0-based индекс
                        col_name = words[col_idx]

                        if self.table:
                            try:
                                col = self.table.headers.index(col_name)
                                if self.table.set_position(row, col):
                                    print(f"\nРедактирование ячейки: строка {row + 1}, {col_name}")
                                    print("Произнесите новое значение")
                                    self.table.display()
                                else:
                                    print("Указанная позиция находится за пределами таблицы")
                            except ValueError:
                                print(f"Столбец '{col_name}' не найден")
                        else:
                            print("Сначала создайте таблицу")
                except (ValueError, IndexError):
                    print("Неверный формат команды редактирования")
                    print("Пример: редактировать строка 1 столбец имя")
                    
            elif "удалить строка" in command:
                words = command.split()
                try:
                    row_idx = words.index("строка") + 1
                    if row_idx < len(words):
                        row = int(words[row_idx]) - 1  # Преобразуем в 0-based индекс
                        if self.table:
                            # Сохраняем данные строки перед удалением для возможности отмены
                            if row < len(self.table.data) - 1:  # -1 чтобы не удалять последнюю пустую строку
                                row_data = self.table.data[row].copy()
                                if self.table.delete_row(row):
                                    self.history.append(('delete_row', row, row_data))
                                    self.logger.info(f"Удалена строка {row + 1}")
                                    print(f"Строка {row + 1} удалена")
                                    self.table.display()
                            else:
                                print("Невозможно удалить указанную строку")
                        else:
                            print("Сначала создайте таблицу")
                except (ValueError, IndexError):
                    print("Неверный формат команды удаления")
                    print("Пример: удалить строка 1")
            else:
                # Если не распознана команда, считаем что это значение для текущей ячейки
                self.set_value(command)

        # Освобождение ресурсов
        self.logger.info("Завершение работы Voice Table Creator")
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
