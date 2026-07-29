import csv
import locale
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import keyboard

import appmethod as app_method
import appsettings as app_settings
import constants


@dataclass
class AppContext:
    settings: app_settings.AppSettings
    read_fields_arg: List[str] = field(default_factory=list)
    filter_date_from_settings: Optional[datetime] = None
    file_from_arg: Optional[Path] = None
    file_to_arg: Optional[Path] = None


class XMLToCVS:
    # read_fields: Перечень полей для чтения (для вывода шапки)
    def __init__(self, initial_fields=None):
        if initial_fields is None:
            self.read_fields = []
        else:
            self.read_fields = list(initial_fields)  # Делаем копию, чтобы не испортить оригинал

    def new_csv_row(self):
        """
        Создаем шаблон строки CSV
        :return: Готовый объект содержащий поля для чтения
        """
        csv_row = {}
        for el in self.read_fields:
            csv_row[el] = ''
        return csv_row

    def save_stream_to_csv(self, ctx: AppContext, data_generator):
        """
        Запись в CSV с потоковым чтением из XML
        :param ctx: контекст приложения
        :param data_generator: yield Построчное чтение XML
        :return:
        """
        # Открываем файл один раз на всё время работы программы
        if ctx.file_to_arg is not None:
            with open(ctx.file_to_arg, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file, delimiter=";")

                # Записываем шапку таблицы
                writer.writerow(self.read_fields)
                # Подменное значение для не обнаруженных столбцах
                missing_value = ""

                # Построчно запрашиваем данные у генератора XML, Цикл FOR здесь двигается со скоростью чтения XML-файла!
                for row in data_generator:
                    if ctx.settings.as_isdebug:
                        print(f"CSV: {row=}\n{row[0]}")
                    values = [row[0].get(h, missing_value) for h in self.read_fields]
                    writer.writerow(values)

    def xml_stream_reader(self, ctx: AppContext):
        """
        Построчное чтение XML
        :param ctx: контекст приложения
        :return:
        """

        if ctx.file_from_arg is None:
            print("Ошибка: Входной файл XML не указан в контексте.")
            return

        filter_date_from_row: datetime | None = None

        # Словарь уникальных ключей (Отбор уникальных значений)
        seen_keys = set()

        aml = app_method.AppMethod()
        et_context = ET.iterparse(ctx.file_from_arg, events=('start', 'end'))

        index = 0
        skip_date = 0
        skip_unique = 0
        csv_row = {}
        key1: str = ''
        key2: str = ''
        key3: str = ''
        for event, elem in et_context:

            # Опционально: ограничение на первые элементы - для отладки
            if ctx.settings.as_max_row_count != 0 and index == (ctx.settings.as_max_row_count + 1):
                break

            if event == 'start':
                # print(f"-> Начало тега: {elem.tag}, Атрибуты: {elem.attrib}")
                # print(f"------------------------------------------------------------------\n{elem.tag} ({index}), Атрибуты: {elem.attrib}")
                if elem.tag == 'row':
                    index += 1
                    if index % 1000 == 0:
                        print(f"Прочитано {index:n} элементов")
                    # Инициализируем результат, одновременно является фильтром
                    csv_row = self.new_csv_row()
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
                    if elem.tag == constants.cnField_Filter:
                        filter_date_from_row = aml.parse_date(text)
                    elif elem.tag == constants.cnField_Filter_U1:
                        key1 = elem.text
                    elif elem.tag == constants.cnField_Filter_U2:
                        key2 = elem.text
                    elif elem.tag == constants.cnField_Filter_U3:
                        key3 = elem.text

                    # Сохраняем выбранные поля
                    if elem.tag in self.read_fields:
                        csv_row[elem.tag] = text
                        # print(f"{elem.tag}: {text}")

                if elem.tag == 'row':
                    # Фильтр на дату (при заполненном значении)
                    if ((
                            ctx.filter_date_from_settings is not None and filter_date_from_row is not None and filter_date_from_row >= ctx.filter_date_from_settings)
                            or ctx.filter_date_from_settings is None):
                        # Контроль на уникальность
                        key = (key1, key2, key3)
                        if ((ctx.settings.as_is_only_unique and key not in seen_keys)
                                or not ctx.settings.as_is_only_unique):
                            # Собираем уникальные элементы только по настройке
                            if ctx.settings.as_is_only_unique:
                                seen_keys.add(key)

                            _print_row(ctx, filter_date_from_row, index, csv_row, False)

                            yield [csv_row]

                        else:
                            _print_row(ctx, filter_date_from_row, index, csv_row, True)
                            skip_unique += 1
                    else:
                        _print_row(ctx, filter_date_from_row, index, csv_row, True)
                        skip_date += 1

                elem.clear()
        print(f"Всего прочитано: {(index - 1):n} (пропущено по дате {skip_date:n}; пропущено по ключу {skip_unique:n})")


def _print_row(ctx: AppContext, filter_date_from_row: datetime | None , index: int, csv_row, is_skip: bool):
    """
    Вспомогательная функция вывода журнала
    :param ctx:
    :param filter_date_from_row:
    :param index:
    :param csv_row:
    :param is_skip:
    :return:
    """
    if ctx.settings.as_isdebug:
        if filter_date_from_row is not None:
            print(f"XML [{index:n}] [{is_skip}]:{filter_date_from_row.strftime('%d.%m.%Y')} => {csv_row=}")
        else:
            print(f"XML [{index:n}] [{is_skip}]: дата не распознана => {csv_row=}")
        print("-" * 40)


def main(ctx: AppContext):
    start = time.perf_counter()
    print(f"\nРазбор начало: {ctx.file_from_arg or 'Не указан'} {datetime.now()}")
    print("-" * 40)

    # Инициализация класса
    xml_to_cvs = XMLToCVS(ctx.read_fields_arg)

    # Инициализируем генератор чтения (он еще не начал читать файл - yeld)
    xml_gen = xml_to_cvs.xml_stream_reader(ctx)

    # Запускаем запись в CSV - передаем генератор в функцию записи.
    # Только сейчас начнется построчное чтение XML и одновременная запись в CSV.
    xml_to_cvs.save_stream_to_csv(ctx, xml_gen)

    end = time.perf_counter()
    print("-" * 40)
    print(f"Разбор окончание: {ctx.file_to_arg or 'Не указан'} {datetime.now()}")
    print(f"Выполнено за {end - start:.4f} сек")


def exit_app(message: str, is_debug: bool):
    """
    Вспомогательная функция для выхода (избавляет от дублирования кода)
    :param message: сообщение
    :param is_debug:
    :return:
    """
    print(message)
    if is_debug:
        print("Нажмите SPACE для выхода...")
        keyboard.wait("space")
    sys.exit(0)


if __name__ == '__main__':
    # Устанавливаем русскую локаль - для вывода чисел в формате n, может влиять на разбор и вывод дат и прочих типов
    locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
    am = app_method.AppMethod()

    # Чтение настроек из файла
    cwd_path = Path.cwd()
    settings_file_name = cwd_path / constants.config_name
    is_exist, settings = am.read_settings(settings_file_name)

    context = AppContext(settings=settings)

    if not is_exist:
        print()
        exit_app(f'Созданы настройки по умолчанию: {settings_file_name}', settings.as_isdebug)
    else:
        # Фильтр на дату
        context.filter_date_from_settings = am.parse_date_settings(settings.as_is_use_filter)
        if context.filter_date_from_settings is not None:
            print(
                f"Фильтр: поле '{constants.cnField_Filter}' >= {context.filter_date_from_settings.strftime('%d.%m.%Y')}")

        # Фильтр на уникальные элементы
        if settings.as_is_only_unique:
            print(
                f"Фильтр: уникальность по составному ключу ['{constants.cnField_Filter_U1}', '{constants.cnField_Filter_U2}', '{constants.cnField_Filter_U3}']")

        if constants.cnIsLocalTest:
            # Локальная отладка. Не проводим проверок - формируем базовую выборку из тестовых данных
            context.read_fields_arg = constants.cnFields_Arg_Test
            context.file_from_arg = Path(
                '../TData/example.xml')  # "as_is_use_filter": "01.01.2025",  "as_is_only_unique": true
            context.file_to_arg = Path('../result.csv')
        else:
            # Стандартный запуск. Разбор выводимых столбцов - имена XML элементов
            context.read_fields_arg = [field.strip() for field in settings.as_fields.split(',')]

            if not any(field.strip() for field in context.read_fields_arg):
                exit_app(f"Не заполнен параметр 'as_fields' в {settings_file_name}", settings.as_isdebug)

            print("Аргументы:", sys.argv)
            if len(sys.argv) < 3:
                exit_app(
                    f"Отсутствуют обязательные аргументы\n1 - полный путь к файлу XML\n2 - полный путь к файлу CSV",
                    settings.as_isdebug)

            context.file_from_arg = Path(sys.argv[1])

            context.file_to_arg = Path(sys.argv[2])

        # 1. Определяем директорию назначения
        dir_path: Path | None = context.file_to_arg.parent if context.file_to_arg else None

        # 2. Проверка входного файла
        if context.file_from_arg is not None and not context.file_from_arg.is_file():
            exit_app(f"Файла '{context.file_from_arg or 'Не указан'}' нет или это не файл", settings.as_isdebug)

        # 3. Проверка выходного каталога
        if dir_path is not None and not dir_path.is_dir():
            exit_app(f"Каталог '{dir_path}' не найден", settings.as_isdebug)

        # 4. Если все проверки пройдены successfully
        print(f"XML: {context.file_from_arg or 'Не указан'}")
        print(f"CSV: {context.file_to_arg or 'Не указан'}")
        print(f"Fields: {context.read_fields_arg}")

        main(context)
