import json
from datetime import datetime
from pathlib import Path

import appsettings as settings


class AppMethod:
    @staticmethod
    def parse_date(date_str: str) -> datetime | None:
        """
        Преобразование строки в дату
        :param date_str: Строка в формате '01 янв 2015', '13 авг 2028'
        :return: Строка преобразованная к дате или None
        """
        month_map_index = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6, 'июл': 7,
                           'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12}

        # Убираем лишние пробелы и разбиваем строку
        parts = date_str.strip().split()
        if len(parts) != 3:
            return None  # raise ValueError(f"Неверный формат даты: '{date_str}'. Ожидается формат 'ДД МММ ГГГГ'.")

        day_str, month_ru, year_str = parts

        # Переводим месяц в английский
        month_index = month_map_index.get(month_ru.lower())
        if not month_index:
            return None  # raise ValueError(f"Неизвестный месяц: '{month_ru}'")

        try:
            return datetime(int(year_str), month_index, int(day_str))
        except ValueError:
            return None

    @staticmethod
    def parse_date_settings(date_str: str) -> datetime | None:
        """
        Преобразование строки в дату
        :param date_str: Строка в формате 'DD.MM.YYYY'
        :return: Строка преобразованная к дате или None
        """
        try:
            return datetime.strptime(date_str, '%d.%m.%Y')
        except (ValueError, TypeError):
            return None

    @staticmethod
    def read_settings(settings_file_path):
        """
        Чтение или создание файла настроек
        :param settings_file_path: Путь к файлу настроек json
        :return: False - создан файл, True - прочитан файл
        """
        result = settings.AppSettings()
        members = [attr for attr in dir(result) if
                   not callable(getattr(result, attr)) and not attr.startswith("__")]

        # Create settings file
        if not Path(settings_file_path).is_file():

            default = {}

            # Default json value
            for member in members:
                default[member] = getattr(result, member)

            # Write default value to json file
            with open(settings_file_path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)

            # Return default value
            return False, result

        with open(settings_file_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        for member in members:
            setattr(result, member, cfg.get(member, getattr(result, member)))

        return True, result
