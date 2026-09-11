@echo off
call conda activate py310

:: 直接使用pyinstaller命令打包
pyinstaller --name="ComfyUIStarterV0.6.7" --noconsole --onefile --clean --add-data="style.qss;." --add-data="icon.ico;." --icon="icon.ico" main.py


:: 复制图标到dist目录确保可以找到
copy /Y icon.ico dist\

echo Done
pause