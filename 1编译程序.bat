@echo off
call conda activate py310

:: 直接使用pyinstaller命令打包
pyinstaller --name="ComfyUIStarterV0.7.0" --noconsole --onefile --clean --collect-all prismqml --add-data="qml;qml" --add-data="icon.ico;." --icon="icon.ico" main_qml.py


:: 复制图标到dist目录确保可以找到
copy /Y icon.ico dist\

echo Done
pause