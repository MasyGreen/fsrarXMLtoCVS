import json
import os

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import src.appmethod as app_method
from appsettings import AppSettings


@pytest.fixture
def am():
    return app_method.AppMethod()


def test_pd_success(am):
    result = am.parse_date_settings("01.01.2020")
    assert result == datetime(2020, 1, 1)


def test_pd_none(am):
    result = am.parse_date_settings("01.012020")
    assert result is None


def test_st_success(am):
    result = am.parse_date("12 сен 2020")
    assert result == datetime(2020, 9, 12)


def test_st_none(am):
    result = am.parse_date("45 янв 2020")
    assert result is None


def test_settings_none(am):
    temp_dir = tempfile.mkdtemp()
    settings_path = Path(temp_dir) / 'test_config.json'
    print(f"{settings_path=}")

    exists, settings = am.read_settings(str(settings_path))

    # 1. Файла действительно не существовало
    assert not exists

    # 2. Проверяем, что файл создан
    assert settings_path.exists()

    # 3. Проверяем, что метод вернул объект нужного класса (исправлено)
    assert isinstance(settings, AppSettings)

    # 4. (Опционально) Можно проверить, что вернулись дефолтные настройки
    assert not settings.as_isdebug

    if settings_path.exists():
        settings_path.unlink()
    os.rmdir(temp_dir)


def test_settings_read(am):
    temp_dir = tempfile.mkdtemp()
    settings_path = Path(temp_dir) / 'test_config.json'
    print(f"{settings_path=}")

    default_config = {'as_isdebug': True, 'as_fields': 'field1,field2', 'as_max_row_count': 50,
                      'as_is_use_filter': '01.06.2025', 'as_is_only_unique': True}
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f)

    exists, settings = am.read_settings(str(settings_path))

    assert exists
    assert settings.as_isdebug
    assert settings.as_fields == 'field1,field2'
    assert settings.as_max_row_count == 50
    assert settings.as_is_use_filter == '01.06.2025'
    assert settings.as_is_only_unique

    if settings_path.exists():
        settings_path.unlink()
    os.rmdir(temp_dir)
