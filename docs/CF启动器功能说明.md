# ComfyUI 启动器功能说明 需求文档 V1.0



## 1. 项目概述 (Project Overview)
用 Python 3.10 + PySide6 实现 Windows 平台不用BAT启动comfyui


## 2. 数据模型 (Data Model)

本模块负责定义应用程序的数据结构，并处理数据的存储和检索。采用 JSON 文件存储数据，以简化数据管理和提高灵活性。


## 3. 核心功能 (Core Functionality)

### 3.1. 启动逻辑

本模块负责构建 ComfyUI 启动命令，并管理子进程的启动、停止和日志输出。

### 3.2. 数据持久化

本模块负责将启动器页面的控件状态保存到 `launcher.ini` 文件中，并在启动时恢复状态。


## 4. 主界面统筹 (Main Interface Coordination)

为了方便后续维护和开发，应用程序将包含一个主界面，用于统筹以下各个独立的功能板块，每个功能板块是一个独立的py文件由主界面调用，单个板块出错不会影响主界面的启动：

*   **启动界面 (Startup Interface)**: 应用程序的入口界面。
*   **设置面板 (Proxy Panel)**: 配置代理服务器设置，包括代理类型、地址、端口、用户名和密码等。
*   **关于面板 (About Panel)**: 显示应用程序的版本信息、版权、许可等。

主界面800x600固定的大小，每个板块都将作为主界面的一个独立视图，并通过左侧的选项卡进行导航，通过清晰的接口与主界面进行通信和数据共享。


### 4.2. 样式管理 (Style Management)

应用程序的 PySide 样式应独立于代码库，通过外部样式表（如 QSS 文件）进行管理。

需要使用os相对路径，因为打包后，exe文件和python_embeded文件夹在同一个目录下。

*   若 `python_embeded/python.exe` 不存在 → 灰化 [启动] 按钮，提示“请先初始化实例”。
*   端口被占用 → 启动时捕获 `QProcess.errorOccurred`，弹 QMessageBox 提示。

## 5. 面板功能

### 启动界面
启动界面的功能需要替代bat文件的功能。
按下启动按钮，启动脚本的内容如下
```cmd
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build
```

启动按钮下面会有启动设置面板

有一个代理开关，如果打开，那么启动脚本前面会增加如下内容。
这里http和https代理网址都是127.0.0.1，端口号设置的7897，调用设置面板里面的代理设置。

```cmd
set http_proxy=http://127.0.0.1:7897
set https_proxy=http://127.0.0.1:7897
```

局域网可访问，有一个开关，

开关打开，启动脚本中会在后面添加liston 和port参数，如下，listen 默认是0.0.0.0，端口号从设置界面中获取。
```cmd
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --listen 0.0.0.0 --port [设置的端口号，默认是8188]
```

低显存开关，打开，启动脚本中会增加 `--lowram` 参数


## 设置界面

代理设置，需要有GUI显示HTTP代理，HTTPS代理，以及端口号，
局域网端口设置，端口号只能输入数字，默认是8188

有一个保存设置的按钮