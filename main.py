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
    as_is_use_filter: str = ''
    as_is_only_unique: bool = False

    def __init__(self):
        self.as_isdebug = False
        self.as_fields = ''
        self.as_max_row_count = 0
        self.as_is_use_filter = ''
        self.as_is_only_unique = False


def read_settings(file_name):
    """
    Чтение или создание файла настроек
    :param file_name: Путь к файлу настроек json
    :return: False - создан файл, True - прочитан файл
    """
    app_settings_result = AppSettings()
    members = [attr for attr in dir(app_settings_result) if
               not callable(getattr(app_settings_result, attr)) and not attr.startswith("__")]

    # Create settings file
    if not Path(file_name).is_file():

        default = {}

        # Default json value
        for member in members:
            default[member] = getattr(app_settings_result, member)

        # Write default value to json file
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

        # Return default value
        return False, app_settings_result

    with open(file_name, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for member in members:
        setattr(app_settings_result, member, cfg.get(member, getattr(app_settings_result, member)))

    return True, app_settings_result


def parse_date(date_str: str):
    """
    Преобразование строки в дату
    :param date_str: Строка в формате '01 янв 2015', '13 авг 2028'
    :return: Строка преобразованная к дате
    """
    # Словарь для перевода сокращённых названий месяцев на английский (для парсинга)
    month_map = {
        'янв': 'Jan',
        'фев': 'Feb',
        'мар': 'Mar',
        'апр': 'Apr',
        'май': 'May',
        'июн': 'Jun',
        'июл': 'Jul',
        'авг': 'Aug',
        'сен': 'Sep',
        'окт': 'Oct',
        'ноя': 'Nov',
        'дек': 'Dec'
    }

    # Убираем лишние пробелы и разбиваем строку
    parts = date_str.strip().split()
    if len(parts) != 3:
        return None
        # raise ValueError(f"Неверный формат даты: '{date_str}'. Ожидается формат 'ДД МММ ГГГГ'.")

    day_str, month_ru, year_str = parts

    # Переводим месяц в английский
    month_en = month_map.get(month_ru.lower())
    if not month_en:
        return None
        # raise ValueError(f"Неизвестный месяц: '{month_ru}'")

    # Собираем строку в формате, который понимает strptime
    normalized_date = f"{day_str} {month_en} {year_str}"

    try:
        return datetime.strptime(normalized_date, "%d %b %Y")
    except ValueError:
        return None


def parse_date_settings(date_str: str):
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except (ValueError, TypeError):
        return None


def new_csv_row(read_fields):
    """
    Создаем шаблон строки CSV
    :param read_fields: Перечень полей для чтения
    :return: Готовый объект содержащий поля для чтения
    """
    csv_row = {}
    for el in read_fields:
        csv_row[el] = ''
    return csv_row


def save_stream_to_csv(csv_path, data_generator, read_fields):
    """
    Запись в CSV с потоковым чтением из XML
    :param csv_path: Путь к файлу CSV
    :param data_generator: yield Построчное чтение XML
    :param read_fields: Перечень полей для чтения (для вывода шапки)
    :return:
    """
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


def xml_stream_reader(file_from, read_fields):
    """
    Построчное чтение XML
    :param file_from: Путь к файлу XML
    :param read_fields: Путь к файлу CSV
    :return:
    """
    global filter_date_from_row
    context = ET.iterparse(file_from, events=('start', 'end'))

    index = 0
    skip_date = 0
    skip_unique = 0
    csv_row = {}
    key1: str = ''
    key2: str = ''
    key3: str = ''
    for event, elem in context:

        # Опционально: ограничение на первые элементы - для отладки
        if app_settings.as_max_row_count != 0 and index == (app_settings.as_max_row_count + 1):
            break

        if event == 'start':
            # print(f"-> Начало тега: {elem.tag}, Атрибуты: {elem.attrib}")
            # print(f"------------------------------------------------------------------\n{elem.tag} ({index}), Атрибуты: {elem.attrib}")
            if elem.tag == 'row':
                index += 1
                if index % 1000 == 0:
                    print(f"Прочитано {index=} элементов")
                # Инициализируем результат, одновременно является фильтром
                csv_row = new_csv_row(read_fields)
                filter_date_from_row = None
                key1 = ''
                key2 = ''
                key3 = ''
                # raw_xml_bytes = ET.tostring(elem, encoding='utf-8')
                # raw_xml_text = raw_xml_bytes.decode('utf-8')
                # print(f"--- Оригинальный XML узла <{elem.tag}> {index} ---")
                # print(raw_xml_text)

        elif event == 'end':
            # Здесь доступны текстовые данные внутри тега
            text = elem.text.strip() if elem.text else ""
            if text:
                # Значение поля для фильтра
                if elem.tag == cnField_Filter:
                    filter_date_from_row = parse_date(text)
                elif elem.tag == cnField_Filter_U1:
                    key1 = elem.text
                elif elem.tag == cnField_Filter_U2:
                    key2 = elem.text
                elif elem.tag == cnField_Filter_U3:
                    key3 = elem.text

                # Сохраняем выбранные поля
                if elem.tag in read_fields:
                    csv_row[elem.tag] = text
                    # print(f"{elem.tag}: {text}")

            if elem.tag == 'row':
                # Фильтр на дату (при заполненном значении)
                if (
                        filter_date_from_settings is not None and filter_date_from_row is not None and filter_date_from_row >= filter_date_from_settings) or filter_date_from_settings is None:
                    # Контроль на уникальность
                    key = (key1, key2, key3)
                    if (app_settings.as_is_only_unique and key not in seen_keys) or not app_settings.as_is_only_unique:
                        # Собираем уникальные элементы только по настройке
                        if app_settings.as_is_only_unique:
                            seen_keys.add(key)

                        yield [csv_row]
                        if app_settings.as_isdebug:
                            print(f"XML:{filter_date_from_row.strftime('%d.%m.%Y')} {csv_row=}")
                            print("-" * 40)
                    else:
                        skip_unique += 1
                else:
                    skip_date += 1

            elem.clear()
    print(f"Всего прочитано: {index - 1} (пропущено по дате {skip_date}; пропущено по ключу {skip_unique})")


def main():
    start = time.perf_counter()
    now = datetime.now()
    print(f"Разбор начало: {file_from_arg} {now}")
    print("-" * 40)
    # Инициализируем генератор чтения (он еще не начал читать файл)
    xml_gen = xml_stream_reader(file_from_arg, read_fields_arg)

    # Передаем генератор в функцию записи.
    # Только сейчас начнется построчное чтение XML и одновременная запись в CSV.
    save_stream_to_csv(file_to_arg, xml_gen, read_fields_arg)

    end = time.perf_counter()
    now = datetime.now()
    print("-" * 40)
    print(f"Разбор окончание: {file_to_arg} {now}")
    print(f"Выполнено за {end - start:.4f} сек")


if __name__ == '__main__':
    cnField_Filter = 'Дата_окончания_действия_лицензии'
    cnField_Filter_U1 = 'Номер_лицензии__соответствующий_номеру_записи_в_реестре'
    cnField_Filter_U2 = 'ИНН_организации_сельскохозяйственного_товаропроизводителя_'
    cnField_Filter_U3 = 'КПП_обособленного_подразделения_организации__осуществляющего_лицензируемый_вид_деятельности'

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
        read_fields_arg = []
        file_from_arg = ''

        # Словарь уникальных ключей
        seen_keys = set()

        # Фильтр на дату
        filter_date_from_settings = parse_date_settings(app_settings.as_is_use_filter)
        if filter_date_from_settings is not None:
            print(
                f"Фильтр: поле '{cnField_Filter}Дата_окончания_действия_лицензии' >= {filter_date_from_settings.strftime('%d.%m.%Y')}")

        # Фильтр на уникальные элементы
        if app_settings.as_is_only_unique:
            print(
                f"Фильтр: уникальность по составному ключу ['{cnField_Filter_U1}', '{cnField_Filter_U2}', '{cnField_Filter_U3}']")

        # Локальная отладка
        local_debug: bool = False

        if local_debug:
            read_fields_arg = [
                'Номер_лицензии__соответствующий_номеру_записи_в_реестре',
                'Дата_окончания_действия_лицензии',
                'Полное_и_сокращенное_наименование_организации_сельскохозяйственного_товаропроизводителя_с_указанием_ее_ОПФ',
                'ИНН_организации_сельскохозяйственного_товаропроизводителя_'
            ]
            file_from_arg = Path('data-20260701t0000-structure-20190918t0000.xml')

            file_to_arg = Path('result.csv')
        else:
            # Разбор выводимых столбцов - имена XML элементов
            read_fields_arg = [field.strip() for field in app_settings.as_fields.split(',')]

            if not any(field.strip() for field in read_fields_arg):
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
            main()
