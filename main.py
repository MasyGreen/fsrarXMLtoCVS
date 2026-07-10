import csv
import json
import sys
from datetime import datetime
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import keyboard


# Настройки
class AppSettings:
    as_isdebug: bool = False
    as_fields: str = ''
    as_max_row_count: int = 0

    def __init__(self):
        self.as_isdebug = False
        self.as_fields = ''
        self.as_max_row_count = 0


# Чтение или создание файла настроек
# False - создан файл, True - прочитан файл
def read_settings(settings_file_name):
    app_settings = AppSettings()
    members = [attr for attr in dir(app_settings) if
               not callable(getattr(app_settings, attr)) and not attr.startswith("__")]

    # Create settings file
    if not Path(settings_file_name).is_file():

        default = {}

        # Default json value
        for member in members:
            default[member] = getattr(app_settings, member)

        # Write default value to json file
        with open(settings_file_name, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

        # Return default value
        return False, app_settings

    with open(settings_file_name, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for member in members:
        setattr(app_settings, member, cfg.get(member, getattr(app_settings, member)))

    return True, app_settings


# Создаем шаблон строки CSV
def new_cvs_row(read_fields):
    cvs_row = {}
    for el in read_fields:
        cvs_row[el] = ''
    return cvs_row


# Запись в CSV
def save_stream_to_csv(csv_path, data_generator, read_fields, app_settings):
    # Открываем файл один раз на всё время работы программы
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")

        # Записываем шапку таблицы
        writer.writerow(read_fields)
        # Подменное значение для не обнаруженных столбцах
        missing_value = ""

        # Построчно запрашиваем данные у генератора XML, Цикл FOR здесь двигается со скоростью чтения XML-файла!
        for row in data_generator:
            if app_settings.as_isdebug:
                print(f"CSV: {row=}\n{row[0]}")
            values = [row[0].get(h, missing_value) for h in read_fields]
            writer.writerow(values)


# Построчное чтение XML с записью в CSV
# file_from - полный путь к файлу XML
# file_to - полный путь к файлу CVS
# max_count - опционально ограничение на чтение первых элементов (0 - без ограничений)
def xml_stream_reader(file_from, read_fields, app_settings):
    context = ET.iterparse(file_from, events=('start', 'end'))

    index = 0
    cvs_row = {}
    for event, elem in context:

        # Опционально: ограничение на первые элементы - для отладки
        if app_settings.as_max_row_count != 0 and index == app_settings.as_max_row_count:
            break

        if event == 'start':
            # print(f"-> Начало тега: {elem.tag}, Атрибуты: {elem.attrib}")
            # print(f"------------------------------------------------------------------\n{elem.tag} ({index}), Атрибуты: {elem.attrib}")
            if elem.tag == 'row':
                index += 1
                if index % 1000 == 0:
                    print(f"Прочитано {index=} элементов")
                cvs_row = new_cvs_row(read_fields)
                # raw_xml_bytes = ET.tostring(elem, encoding='utf-8')
                # raw_xml_text = raw_xml_bytes.decode('utf-8')
                # print(f"--- Оригинальный XML узла <{elem.tag}> {index} ---")
                # print(raw_xml_text)

        elif event == 'end':
            # Здесь доступны текстовые данные внутри тега
            text = elem.text.strip() if elem.text else ""
            if text:
                if elem.tag in read_fields:
                    cvs_row[elem.tag] = text
                    # print(f"{elem.tag}: {text}")

            if elem.tag == 'row':
                yield [cvs_row]
                if app_settings.as_isdebug:
                    print(f"XML: {cvs_row=}")
                    print("-" * 40)

            elem.clear()
    print(f"Всего прочитано: {index}")


def main(app_settings):
    start = time.perf_counter()
    now = datetime.now()
    print(f"Разбор начало: {file_from_arg} {now}")

    # Инициализируем генератор чтения (он еще не начал читать файл)
    xml_gen = xml_stream_reader(file_from_arg, read_fields_arg, app_settings)

    # Передаем генератор в функцию записи.
    # Только сейчас начнется построчное чтение XML и одновременная запись в CSV.
    save_stream_to_csv(file_to_arg, xml_gen, read_fields_arg, app_settings)

    end = time.perf_counter()
    now = datetime.now()
    print(f"Разбор окончание: {file_to_arg} {now}")
    print(f"Выполнено за {end - start:.4f} сек")


if __name__ == '__main__':
    cwd_path = Path.cwd()
    config_name = 'config.json'
    settings_file_name = cwd_path / config_name;
    is_exist, app_settings = read_settings(settings_file_name)

    if not is_exist:
        print(f'Созданы настройки по умолчанию: {settings_file_name}')
        print(f'Нажмите пробел (Space) для продолжения...')
        if app_settings.as_isdebug:
            keyboard.wait("space")
        sys.exit(0)
    else:
        read_fields_arg = {}
        file_from_arg = ''

        # Локальная отладка
        local_debug: bool = False

        if local_debug:
            read_fields_arg = {
                'Полное_и_сокращенное_наименование_организации_сельскохозяйственного_товаропроизводителя_с_указанием_ее_ОПФ',
                'ИНН_организации_сельскохозяйственного_товаропроизводителя_',
                'Дата_окончания_действия_лицензии'}
            file_from_arg = Path('data-20260701t0000-structure-20190918t0000.xml')

            file_to_arg = Path('result.csv')
        else:
            # Разбор выводимых столбцов - имена XML элементов

            read_fields_arg = set(app_settings.as_fields.split(','))

            if read_fields_arg == {''}:
                print(f"Не заполнен параметр 'as_fields' в {settings_file_name}")
                print(f'Нажмите пробел (Space) для продолжения...')
                if app_settings.as_isdebug:
                    keyboard.wait("space")
                sys.exit(0)

            print("Аргументы:", sys.argv)
            if len(sys.argv) < 3:
                print(f"Отсутствуют обязательные аргументы\n1 - полный путь к файлу XML\n2 - полный путь к файлу CSV")
                print(f'Нажмите пробел (Space) для продолжения...')
                if app_settings.as_isdebug:
                    keyboard.wait("space")
                sys.exit(0)

            file_from_arg = Path(sys.argv[1])

            file_to_arg = Path(sys.argv[2])

        dir_path = file_to_arg.parent  # Path-объект директории

        if not file_from_arg.is_file():
            print(f"Файла '{file_from_arg}' нет или это не файл")
            if app_settings.as_isdebug:
                keyboard.wait("space")
            sys.exit(0)
        elif not dir_path.is_dir():
            print(f"Каталога '{dir_path}' нет")
            if app_settings.as_isdebug:
                keyboard.wait("space")
            sys.exit(0)
        else:
            print(f"XML: {file_from_arg=}")
            print(f"CSV: {file_to_arg=}")
            print(f"Fields: {read_fields_arg}")
            main(app_settings)
