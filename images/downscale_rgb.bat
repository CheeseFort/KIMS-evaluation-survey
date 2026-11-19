@echo off
setlocal

if "%~1"=="" (
    echo Drag RGB images or folders onto this BAT file.
    pause
    exit /b
)

:process
if "%~1"=="" goto done

python "%~dp0downscale_rgb.py" "%~1" -o "%~dp0rgb_%~n1.jpg"

shift
goto process

:done
echo.
echo Finished.
