# ComfyUI 启动器

![Version](https://img.shields.io/badge/version-0.7.0-blue)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.x-41CD52?logo=qt&logoColor=white)
![PrismQML](https://img.shields.io/badge/PrismQML-0.4.2-purple)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)
![License](https://img.shields.io/badge/License-MIT-yellow)

一个面向 Windows 的 ComfyUI 图形化启动器：不再手写、修改 `.bat` 文件，用图形界面完成 **启动 / 停止、版本切换、自定义节点管理、依赖安装、代理与启动参数配置**。

界面基于 **QML + PrismQML** 构建，逻辑由 Python（PySide6）后端驱动，配置全部本地持久化，开箱即用。

> 本项目针对 **ComfyUI 官方便携版（python_embeded）** 设计，需与 `python_embeded` 文件夹放在同一级目录。

---

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [打包发布](#打包发布)
- [项目结构](#项目结构)
- [配置文件说明](#配置文件说明)
- [常见问题](#常见问题)
- [技术栈](#技术栈)
- [致谢](#致谢)
- [许可证](#许可证)

---

## 功能特性

### 启动页

- **一键启动 / 停止 / 重启** ComfyUI，实时显示运行状态
- **强行停止**：ComfyUI 卡死或无响应时，强制结束所有相关 `python.exe` 进程
- **运行日志**：实时输出启动日志，支持「清空日志 / 复制日志 / 保存到文件」
- **文件夹快捷访问**：一键打开根目录、节点目录、模型目录、用户工作流、输入文件夹、输出文件夹

### 版本管理

- 拉取并展示 ComfyUI **稳定版 / 开发版** 版本列表（含提交号与日期）
- 标记「当前版本」，一键**切换/回滚**到指定提交
- 支持**切换更新源**、**启用代理**、手动刷新版本列表
- 切换前给出「会丢失未提交更改」的确认提示

### 节点管理

- **自定义节点安装**：填写 Git 地址一键 `git clone` 安装（可选走代理）
- **自定义节点管理**：分页列表展示，支持启用 / 禁用节点、打开节点目录、刷新列表、获取本地版本
- **单节点版本管理**：查看单个节点的版本历史并切换
- **依赖管理**
  - 镜像源切换（清华、阿里云、中科大、华为云、腾讯云等）
  - 操作类型：安装单个依赖 / 卸载单个依赖 / WHL 安装 / 依赖文件安装
  - 一键安装「ComfyUI 本体 + 前端 + 工作流 + 文档」依赖
  - 导出依赖列表、打开本体依赖文件
  - 针对单个节点安装其 `requirements.txt`（右键「安装依赖」按钮可直接打开该依赖文件）

### 设置

- **代理设置**：启用代理、代理类型（系统代理 / SOCKS5）、代理地址与端口
- **局域网设置**：启用局域网访问、监听地址、自定义端口
- **Python 解释器路径**：支持使用自定义 `python.exe`（便携版之外的环境）
- **高级启动参数**：自定义输出/输入目录、显存模式与预留显存、禁用元数据（图片不保存工作流）、Manager 重启命令接管及关键词
- **当前启动参数**实时预览，保存后立即生效

### 关于

- 展示应用版本、功能简介与版权信息

---

## 环境要求

- **操作系统**：Windows 10 / 11
- **Python**：3.10
- **ComfyUI**：官方便携版（目录内含 `python_embeded/` 与 `ComfyUI/`）

Python 依赖见 [requirements.txt](requirements.txt)：

```
PySide6>=6.4.0
PySide6-Fluent-Widgets==1.8.3   # 仅旧版 Fluent 界面（main.py）需要
prismqml>=0.4.2
pyinstaller>=5.6.2
gitpython>=3.1.30
```

---

## 快速开始

### 1. 下载发布版（推荐）

1. 前往 Releases 下载最新的 `ComfyUIStarterV0.7.0.exe`
2. 将 exe 放到 **ComfyUI 便携版根目录**（即与 `python_embeded` 文件夹同级）
3. 双击运行即可

目录结构示意：

```
ComfyUI_windows_portable/
├─ python_embeded/
├─ ComfyUI/
├─ update/
└─ ComfyUIStarterV0.7.0.exe   ← 启动器放在这里
```

### 2. 从源码运行

```bash
# 1) 克隆仓库
git clone <仓库地址>
cd CF启动管理器fluent版

# 2) 安装依赖（建议使用虚拟环境 / conda 环境）
pip install -r requirements.txt

# 3) 启动
python main_qml.py
```

也可以直接双击 `0运行GUI.bat`（默认调用 conda 环境 `py310`）。

> 首次运行会自动创建 `starter/` 目录并生成默认配置文件。

---

## 打包发布

双击 `1编译程序.bat`，或手动执行：

```bash
pyinstaller --name="ComfyUIStarterV0.7.0" --noconsole --onefile --clean ^
  --collect-all prismqml --add-data="qml;qml" --add-data="icon.ico;." ^
  --icon="icon.ico" main_qml.py
```

打包产物位于 `dist/ComfyUIStarterV0.7.0.exe`。

---

## 项目结构

```
CF启动管理器fluent版/
├─ main_qml.py                 # 新版 QML 界面入口
├─ main.py                     # 旧版 Fluent Widgets 界面入口
├─ qml/                        # QML 界面（一个页面一个文件）
│  ├─ StartupPage.qml          #   启动页
│  ├─ VersionPage.qml          #   版本管理页
│  ├─ NodesPage.qml            #   节点管理页
│  ├─ SettingsPage.qml         #   设置页
│  └─ AboutPage.qml            #   关于页
├─ qml_backend/                # 各页面的 Python 后端（通过 Property/Slot 暴露给 QML）
│  ├─ startup_backend.py
│  ├─ version_backend.py
│  ├─ nodes_backend.py
│  ├─ node_version_backend.py
│  ├─ settings_backend.py
│  └─ about_backend.py
├─ data_model.py               # 配置读取与持久化（INI）
├─ process_manager.py          # ComfyUI 进程的启动/停止/日志
├─ nodes_local_info.py         # 本地节点信息读取
├─ nodes_update_single.py      # 单节点版本与更新逻辑
├─ startup_panel.py …          # 旧版 Fluent 界面（对应 main.py）
├─ style.qss                   # 旧版界面样式表
├─ icon.ico / icon.svg         # 应用图标
├─ requirements.txt
├─ 0运行GUI.bat                # 一键运行（源码）
├─ 1编译程序.bat               # 一键打包
└─ docs/                       # 需求说明与启动参数文档
```

---

## 配置文件说明

所有配置保存在程序目录下的 `starter/` 文件夹中，均为标准 INI 格式，可直接用文本编辑器查看：

| 文件 | 用途 |
| --- | --- |
| `starter/launcher.ini` | 代理、局域网、Python 路径、高级启动参数等设置 |
| `starter/nodes.ini` | 节点管理的镜像源、代理等设置 |
| `starter/version.ini` | 版本管理的更新源、代理等设置 |
| `starter/git.ini` | Git 相关配置 |
| `starter/nodes_list.ini` | 自定义节点列表 |
| `starter/nodes_list_git.ini` | 自定义节点的 Git 信息缓存 |

---

## 常见问题

**Q：启动时提示「请先初始化实例 / 找不到 python_embeded」？**
A：请确认 exe（或源码目录）与 `python_embeded` 文件夹处于同一级目录；或到「设置 → Python 路径设置」中手动指定 `python.exe`。

**Q：启动/更新节点时下载很慢或失败？**
A：在对应页面勾选「启用代理」，或在「设置 → 代理设置」中配置代理地址与端口；依赖安装可在「节点管理 → 依赖管理」中切换国内镜像源。

**Q：切换 ComfyUI 版本后我的改动不见了？**
A：版本切换基于 Git checkout，会丢弃未提交的本地修改，切换前请先自行备份或提交。

**Q：窗口可以调整大小吗？**
A：可以。初始为 800x600，可自由拉伸，最小 600x600。

---

## 技术栈

- Python 3.10 + PySide6（Qt 6）
- QML / Qt Quick 界面，[PrismQML](https://pypi.org/project/prismqml/) 提供窗口与控件
- GitPython / Git 命令行：版本与节点仓库管理
- ConfigParser（INI）：配置持久化
- PyInstaller：单文件打包

---

## 致谢

- [PrismQML](https://pypi.org/project/prismqml/) —— 提供现代化 QML 窗口与控件
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) —— 本项目所服务的项目

---

## 许可证

本项目采用 MIT 许可证，详见 `LICENSE` 文件。
