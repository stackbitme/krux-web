@echo off
rem Duplo clique para abrir o Simulador Krux no navegador (Windows).
cd /d "%~dp0"
where py >nul 2>nul && (py serve.py) || (python serve.py)
if errorlevel 1 (
  echo.
  echo Nao encontrei o Python. Instale em https://www.python.org/downloads/ e tente de novo.
  pause
)
