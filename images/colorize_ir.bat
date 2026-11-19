
@echo off
setlocal

if "%~1"=="" (
    echo Drag PNG files onto this BAT file.
    pause
    exit /b
)

:process
if "%~1"=="" goto done

python "%~dp0colorize_ir.py" "%~1" -o "%~dp0%~n1_ir.jpg"

shift
goto process

:done
echo.
echo Finished.
puase