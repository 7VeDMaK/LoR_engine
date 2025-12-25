@echo off
title LoR Combat Engine Launcher
echo Запускаю боевую систему...
echo.

:: Переходим в папку, где лежит этот скрипт (чтобы пути не ломались)
cd /d "%~dp0"

:: Проверка, установлен ли streamlit
streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Streamlit не найден!
    echo Пожалуйста, установите его командой: pip install streamlit
    echo.
    pause
    exit /b
)

:: Запуск приложения
streamlit run app.py

:: Если приложение закрылось с ошибкой, не закрывать окно сразу
if %errorlevel% neq 0 (
    echo.
    echo Произошла ошибка при выполнении.
    pause
)