@echo off
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 설치해주세요.
    echo 설치 시 "Add python.exe to PATH"를 꼭 체크해주세요.
    pause
    exit /b
)

if not exist ".venv" (
    echo 처음 실행이라 필요한 프로그램을 설치합니다. 몇 분 걸릴 수 있어요...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

streamlit run app.py
