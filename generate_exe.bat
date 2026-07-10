CHCP 65001
rmdir "build" /s /q
rmdir "dist" /s /q
@call .venv\Scripts\activate.bat
pyinstaller _script.spec
rmdir "build" /s /q