import csv
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import constants
import main as _main

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from appsettings import AppSettings


@pytest.fixture
def main():
    return _main


def test_work(main):
    temp_dir = tempfile.mkdtemp()

    settings = AppSettings()
    settings.as_is_only_unique = True
    settings.as_is_use_filter = "01.01.2025"
    settings.as_max_row_count = 4
    settings.as_fields = constants.cnFields_Arg_Test
    settings.as_isdebug = True

    ctx = main.AppContext(settings=settings)
    ctx.file_from_arg = Path("TData\\example.xml")
    ctx.file_to_arg = Path(temp_dir) / 'outer.csv'
    ctx.read_fields_arg = constants.cnFields_Arg_Test
    ctx.filter_date_from_settings = datetime(2025, 1, 1)

    print(f"\nРезультат: {ctx.file_to_arg or ''}")

    assert ctx.file_from_arg is not None and ctx.file_from_arg.exists()
    assert ctx.file_to_arg is not None and not ctx.file_to_arg.exists()

    main.main(ctx)

    assert ctx.file_to_arg is not None and ctx.file_to_arg.exists()

    csv_rows = []
    with open(ctx.file_to_arg, mode='r', encoding='utf-8') as file:
        # DictReader автоматически превращает каждую строку в словарь,
        # где ключи — это названия колонок из первой строки CSV
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            # Добавляем полученный словарь в наш список
            csv_rows.append(row)

    for row in csv_rows:
        print(row)
        # Выводятся только значения без первого столбца с заголовками (заголовки:значения)
        # {'\ufeffНомер_лицензии__соответствующий_номеру_записи_в_реестре;Дата_окончания_действия_лицензии;Полное_и_сокращенное_наименование_организации_сельскохозяйственного_товаропроизводителя_с_указанием_ее_ОПФ;ИНН_организации_сельскохозяйственного_товаропроизводителя_':
        # '50РПА0022255;04 дек 2029;"Общество с ограниченной ответственностью ""Альбион-2002"" Сокращенно: ООО ""Альбион-2002""";5257056036'}
    assert len(csv_rows) == 2


def test_read_xml(main):
    temp_dir = tempfile.mkdtemp()

    # Переопределение полей вывода
    constants.cnFields_Arg_Test = ["name", "id", "date"]

    settings = AppSettings()
    settings.as_is_only_unique = True
    settings.as_is_use_filter = "01.01.2025"
    settings.as_max_row_count = 10
    settings.as_fields = constants.cnFields_Arg_Test
    settings.as_isdebug = True

    ctx = main.AppContext(settings=settings)
    ctx.file_from_arg = Path(temp_dir) / 'inner.xml'
    ctx.file_to_arg = Path(temp_dir) / 'outer.csv'
    ctx.read_fields_arg = constants.cnFields_Arg_Test
    ctx.filter_date_from_settings = datetime(2025, 1, 1)

    print(f"\nВходящий файл: {ctx.file_from_arg or ''}")
    print(f"Результат: {ctx.file_to_arg or ''}")

    # Создаем тестовый файл
    rows = [
        {'name': '1', 'id': '1001', 'date': '01 янв 2026'},
        {'name': '2', 'id': '1002', 'date': '01 янв 2026'},
        {'name': '3 error id', 'id': '1002', 'date': '01 янв 2026'},
        {'name': '4 error date', 'id': '1003', 'date': '01 янв 2020'},
    ]
    _create_xml(ctx.file_from_arg, rows)

    assert ctx.file_from_arg is not None and ctx.file_from_arg.exists()
    assert ctx.file_to_arg is not None and not ctx.file_to_arg.exists()

    # Переопределение поля с датой
    constants.cnField_Filter = "date"

    # Переопределение поля с уникальными ключами
    constants.cnField_Filter_U1 = "id"
    constants.cnField_Filter_U2 = ""
    constants.cnField_Filter_U3 = ""

    # 1 Полные ограничения - из 4, 2 ошибочных
    xml_to_cvs = main.XMLToCVS(ctx.read_fields_arg)
    xml_gen = list(xml_to_cvs.xml_stream_reader(ctx))  # yeld получаем весь список
    assert len(xml_gen) == 2

    # 2 Разрешены дубли - из 4, 1 ошибочное
    ctx.settings.as_is_only_unique = False
    xml_to_cvs = main.XMLToCVS(ctx.read_fields_arg)
    xml_gen = list(xml_to_cvs.xml_stream_reader(ctx))  # yeld получаем весь список
    assert len(xml_gen) == 3

    # 3 Полное чтение
    ctx.settings.as_is_only_unique = False
    ctx.filter_date_from_settings = None
    xml_to_cvs = main.XMLToCVS(ctx.read_fields_arg)
    xml_gen = list(xml_to_cvs.xml_stream_reader(ctx))  # yeld получаем весь список
    assert len(xml_gen) == 4


def _create_xml(xml_path, rows):
    """
    Вспомогательная функция записи в файл
    :param xml_path: путь к файлу
    :param rows: строки []
    :return:
    """
    root = ET.Element('data')
    for row_data in rows:
        row_elem = ET.SubElement(root, 'row')
        for tag, text in row_data.items():
            child = ET.SubElement(row_elem, tag)
            child.text = text
    tree = ET.ElementTree(root)
    tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
