@echo off
setlocal

if "%~1"=="" (
    echo Drag PNG files onto this BAT file.
    pause
    exit /b
)

:process
if "%~1"=="" goto done

python "%~dp0colorize_ir.py" "%~1" -o "%~dp0ir_%~n1.jpg"

shift
goto process

:done
echo.
echo Finished.
puase
