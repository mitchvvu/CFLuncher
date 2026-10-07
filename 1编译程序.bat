@echo off
call conda activate py310

:: Build with the spec file (unused Qt modules/translations are stripped to reduce size)
pyinstaller --clean ComfyUIStarter.spec

:: Copy the icon to the dist folder so it can be found at runtime
copy /Y icon.ico dist\

echo Done
pause
