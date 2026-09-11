import os
from PySide6.QtCore import QObject, Signal, QProcess
import locale

class ComfyUIProcessManager(QObject):
    # 定义信号
    log_signal = Signal(str)
    status_changed = Signal(bool)  # True表示启动，False表示停止
    error_occurred = Signal(str)  # 错误信息
    
    def __init__(self, data_model):
        super().__init__()
        self.data_model = data_model
        self.process = None
        self._intentional_kill = False  # 标记是否是主动终止进程
        self._auto_restart = True  # 标记是否在进程终止时自动重启
        self._current_pid = None  # 存储当前cmd.exe进程的PID
        self._python_pid = None  # 存储当前python.exe进程的PID
        self._additional_python_pids = []  # 存储额外的python.exe进程ID
        self.proxy_commands = []  # 存储代理设置命令
        self.initialize_process()
    
    def initialize_process(self):
        """初始化QProcess对象"""
        if self.process is None:
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.errorOccurred.connect(self.handle_error)
            self.process.finished.connect(self.process_finished)
    
    def start_comfyui(self):
        """启动ComfyUI"""
        self.initialize_process()
        
        # 重置自动重启标志为True
        self._auto_restart = True
        
        # 检查代理是否启用并获取代理类型
        proxy_enabled = self.data_model.get_bool('proxy', 'enabled')
        proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
        
        # 输出详细的代理调试信息
        if proxy_enabled:
            http_proxy = self.data_model.get_value('proxy', 'http_proxy')
            https_proxy = self.data_model.get_value('proxy', 'https_proxy')
            proxy_port = self.data_model.get_value('proxy', 'port')
            
            # 根据代理类型构建日志信息和代理URL
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == 'socks5':
                proxy_url_format = f"socks5://{http_proxy}:{proxy_port}"
                self.log_signal.emit("> 代理状态: 已启用\n> 代理类型: Socks5代理\n")
                self.proxy_commands = ["使用Socks5代理"]
            else:  # 系统代理
                proxy_url_format = f"http://{http_proxy}:{proxy_port}"
                self.log_signal.emit("> 代理状态: 已启用\n> 代理类型: 系统代理\n")
                self.proxy_commands = ["使用系统代理"]
            
            # 获取当前环境变量
            env = QProcess.systemEnvironment()
            
            # 创建环境变量列表
            new_env = []
            for var in env:
                # 跳过可能已存在的代理环境变量
                if not var.startswith("http_proxy=") and not var.startswith("https_proxy="):
                    new_env.append(var)
            
            # 添加新的代理环境变量
            new_env.append(f"http_proxy={proxy_url_format}")
            new_env.append(f"https_proxy={proxy_url_format}")
            
            # 设置环境变量
            self.process.setEnvironment(new_env)
        else:
            # 如果代理未启用，只输出未使用代理的信息，不涉及代理类型
            self.log_signal.emit("> 代理状态: 未启用\n")
            self.proxy_commands = []
        
        # 构建启动命令
        command = self.build_command()
        
        # 启动进程
        self.process.start(command[0], command[1:])
        
        if self.process.waitForStarted(3000):
            # 获取并记录cmd.exe进程ID
            try:
                cmd_pid = self.process.processId()
                self.log_signal.emit(f"\n\nComfyUI 正在启动...\nCMD进程ID: {cmd_pid}\n")
                # 保存cmd进程ID
                self._current_pid = cmd_pid
                
                # 等待一段时间，让python.exe进程启动
                import time
                time.sleep(2)
                
                # 查找对应的python.exe进程ID
                self._find_python_process()
                
            except Exception as e:
                self.log_signal.emit(f"\n\nComfyUI 正在启动...\n无法获取进程ID: {str(e)}\n")
            
            # 发送状态变化信号
            self.status_changed.emit(True)
            print(f"进程启动，发送状态变化信号: True")
            return True
        else:
            self.log_signal.emit("\n\n启动失败！\n")
            # 确保在启动失败时也发送状态变化信号
            self.status_changed.emit(False)
            print(f"进程启动失败，发送状态变化信号: False")
            return False
            
    def _find_python_process(self):
        """查找与cmd.exe关联的python.exe进程"""
        if self._current_pid is None:
            self.log_signal.emit("无法查找python进程：cmd进程ID未知\n")
            return
            
        try:
            import subprocess
            import re
            
            # 使用wmic命令查找cmd.exe的子进程
            cmd = f'wmic process where "ParentProcessId={self._current_pid}" get Caption,ProcessId'
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 存储找到的所有python.exe进程ID
            python_pids = []
            
            # 解析输出，查找python.exe进程
            for line in result.stdout.splitlines():
                if 'python.exe' in line.lower():
                    # 提取进程ID
                    match = re.search(r'\d+', line)
                    if match:
                        python_pid = int(match.group())
                        python_pids.append(python_pid)
                        self.log_signal.emit(f"找到关联的python.exe进程ID: {python_pid}\n")
            
            if python_pids:
                # 保存第一个找到的python.exe进程ID作为主进程ID
                self._python_pid = python_pids[0]
                
                # 如果找到多个python.exe进程，记录它们
                if len(python_pids) > 1:
                    self._additional_python_pids = python_pids[1:]
                    self.log_signal.emit(f"找到额外的python.exe进程: {self._additional_python_pids}\n")
                else:
                    self._additional_python_pids = []
                return
            
            self.log_signal.emit("未找到关联的python.exe进程\n")
            self._additional_python_pids = []
        except Exception as e:
            self.log_signal.emit(f"查找python.exe进程时出错: {str(e)}\n")
            self._python_pid = None
            self._additional_python_pids = []
    
    def stop_comfyui(self):
        """停止ComfyUI"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            # 设置标记，表示这是主动终止进程
            self._intentional_kill = True
            # 禁用自动重启，因为这是用户主动停止
            self._auto_restart = False
            
            # 先尝试正常终止进程
            self.process.kill()
            
            import subprocess
            
            # 终止主python.exe进程
            if self._python_pid is not None:
                try:
                    self.log_signal.emit(f"正在终止python.exe进程 (PID: {self._python_pid})\n")
                    # 使用进程ID终止python.exe进程及其子进程
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._python_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log_signal.emit(f"已终止python.exe进程 (PID: {self._python_pid})\n")
                except Exception as e:
                    self.log_signal.emit(f"终止python.exe进程时出错: {str(e)}\n")
            else:
                self.log_signal.emit("未找到主python.exe进程ID，无法精确终止\n")
            
            # 终止额外的python.exe进程
            for pid in self._additional_python_pids:
                try:
                    self.log_signal.emit(f"正在终止额外的python.exe进程 (PID: {pid})\n")
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log_signal.emit(f"已终止额外的python.exe进程 (PID: {pid})\n")
                except Exception as e:
                    self.log_signal.emit(f"终止额外的python.exe进程时出错: {str(e)}\n")
            
            # 终止cmd.exe进程
            cmd_pid = self._current_pid
            if cmd_pid is None:
                try:
                    cmd_pid = self.process.processId()
                    self.log_signal.emit(f"使用当前cmd.exe进程ID: {cmd_pid}\n")
                except Exception as e:
                    self.log_signal.emit(f"无法获取cmd.exe进程ID: {str(e)}\n")
            else:
                self.log_signal.emit(f"使用记录的cmd.exe进程ID: {cmd_pid}\n")
            
            # 如果有有效的cmd.exe进程ID，使用taskkill命令强制终止该进程及其所有子进程
            if cmd_pid is not None:
                try:
                    # 使用进程ID终止cmd.exe进程及其子进程
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(cmd_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log_signal.emit(f"已终止cmd.exe进程 (PID: {cmd_pid})及其所有子进程\n")
                except Exception as e:
                    self.log_signal.emit(f"终止cmd.exe进程时出错: {str(e)}\n")
            
            self.log_signal.emit("ComfyUI 已停止\n")
            # 发送状态变化信号
            self.status_changed.emit(False)
            print(f"进程停止，发送状态变化信号: False")
            # 重置进程ID
            self._current_pid = None
            self._python_pid = None
            self._additional_python_pids = []
            return True
        # 如果进程不在运行状态，也发送一次状态信号
        self.status_changed.emit(False)
        print(f"进程已经不在运行，发送状态变化信号: False")
        return False

    def is_running(self):
        """检查ComfyUI进程是否正在运行"""
        return self.process and self.process.state() == QProcess.ProcessState.Running

    def wait_for_finished(self, msecs=3000):
        """等待进程结束"""
        if self.process:
            return self.process.waitForFinished(msecs)
        return True

    def restart_comfyui(self):
        """重启ComfyUI"""
        self.log_signal.emit("正在重启 ComfyUI...\n")
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            # 先停止当前进程
            # 使用stop_comfyui方法停止进程，该方法会处理_current_pid
            if self.stop_comfyui():
                # 等待进程完全停止
                if self.wait_for_finished(3000):
                    # 然后重新启动
                    return self.start_comfyui()
                else:
                    # 如果等待超时，尝试强制终止
                    self.force_kill()
                    if self.wait_for_finished(3000):
                        return self.start_comfyui()
                    else:
                        self.log_signal.emit("重启失败：无法停止当前进程\n")
                        self.error_occurred.emit("无法停止当前进程，请手动停止后再启动。\n")
                        return False
            else:
                self.log_signal.emit("重启失败：无法停止当前进程\n")
                self.error_occurred.emit("无法停止当前进程，请手动停止后再启动。\n")
                return False
        else:
            # 如果进程不在运行，直接启动
            return self.start_comfyui()
    
    def build_command(self):
        """构建启动命令"""
        # 基本命令
        command = ["cmd.exe", "/c"]
        
        # 尝试从settings_panel获取ComfyUI路径
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        # 如果能获取到settings_panel实例，使用其get_comfyui_path方法获取ComfyUI路径
        if main_window and hasattr(main_window, 'settings_panel'):
            comfyui_path = main_window.settings_panel.get_comfyui_path()
            # 获取Python路径
            custom_path_enabled = self.data_model.get_bool('paths', 'custom_comfyui_path_enabled')
            
            if custom_path_enabled:
                python_exe_path = self.data_model.get_value('paths', 'comfyui_path')
                if python_exe_path and os.path.exists(python_exe_path):
                    # 使用自定义的python.exe路径
                    python_exe_dir = os.path.dirname(python_exe_path)
                    # 使用settings_panel获取的ComfyUI路径
                    main_py = os.path.join(comfyui_path, "main.py")
                    
                    # 添加cd命令切换到python_embeded所在目录
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in python_exe_dir:
                        command.extend(["cd", f"\"{python_exe_dir}\"", "&"])
                    else:
                        command.extend(["cd", python_exe_dir, "&"])
                    
                    # 使用python.exe的完整路径
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in python_exe_path:
                        command.append(f"\"{python_exe_path}\"")
                    else:
                        command.append(python_exe_path)
                        
                    command.append("-s")
                    
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in main_py:
                        command.append(f"\"{main_py}\"")
                    else:
                        command.append(main_py)
                        
                    command.append("--windows-standalone-build")
                else:
                    # 如果自定义路径为空或不存在，使用默认路径
                    command.append(".\python_embeded\python.exe")
                    command.append("-s")
                    command.append(os.path.join(comfyui_path, "main.py"))
                    command.append("--windows-standalone-build")
            else:
                # 使用默认路径
                command.append(".\python_embeded\python.exe")
                command.append("-s")
                command.append(os.path.join(comfyui_path, "main.py"))
                command.append("--windows-standalone-build")
        else:
            # 如果无法获取settings_panel实例，使用原有逻辑
            # 获取Python路径
            custom_path_enabled = self.data_model.get_bool('paths', 'custom_comfyui_path_enabled')
            
            if custom_path_enabled:
                python_exe_path = self.data_model.get_value('paths', 'comfyui_path')
                if python_exe_path and os.path.exists(python_exe_path):
                    # 使用自定义的python.exe路径
                    python_exe_dir = os.path.dirname(python_exe_path)
                    # 假设ComfyUI目录在python_embeded的上一级目录
                    comfyui_dir = os.path.dirname(python_exe_dir)
                    main_py = os.path.join(comfyui_dir, "ComfyUI", "main.py")
                    
                    # 添加cd命令切换到python_embeded所在目录
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in python_exe_dir:
                        command.extend(["cd", f"\"{python_exe_dir}\"", "&"])
                    else:
                        command.extend(["cd", python_exe_dir, "&"])
                    
                    # 使用python.exe的完整路径
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in python_exe_path:
                        command.append(f"\"{python_exe_path}\"")
                    else:
                        command.append(python_exe_path)
                        
                    command.append("-s")
                    
                    # 如果路径包含空格，需要用双引号括起来
                    if " " in main_py:
                        command.append(f"\"{main_py}\"")
                    else:
                        command.append(main_py)
                        
                    command.append("--windows-standalone-build")
                else:
                    # 如果自定义路径为空或不存在，使用默认路径
                    command.append(".\python_embeded\python.exe")
                    command.append("-s")
                    command.append("ComfyUI\main.py")
                    command.append("--windows-standalone-build")
            else:
                # 使用默认路径
                command.append(".\python_embeded\python.exe")
                command.append("-s")
                command.append("ComfyUI\main.py")
                command.append("--windows-standalone-build")
        
        # 添加局域网访问设置
        if self.data_model.get_bool('network', 'lan_access'):
            listen = self.data_model.get_value('network', 'listen')
            command.append("--listen")
            command.append(listen)
        
        # 添加自定义端口设置
        if self.data_model.get_bool('network', 'custom_port_enabled'):
            port = self.data_model.get_value('network', 'port')
            command.append("--port")
            command.append(port)
        
        # 添加高级启动参数
        if self.data_model.get_bool('advanced', 'reserve_vram_enabled'):
            reserve_vram_value = self.data_model.get_value('advanced', 'reserve_vram')
            if reserve_vram_value:
                command.append(f"--reserve-vram {reserve_vram_value}")
        # 输出目录
        if self.data_model.get_bool('advanced', 'output_dir_enabled'):
            output_dir = self.data_model.get_value('advanced', 'output_dir')
            if output_dir:
                # 不再转换路径分隔符
                # output_dir = output_dir.replace('\\', '/')
                command.append("--output-directory")
                command.append(f"\"{ output_dir}\"")
        
        # 输入目录
        if self.data_model.get_bool('advanced', 'input_dir_enabled'):
            input_dir = self.data_model.get_value('advanced', 'input_dir')
            if input_dir:
                # 不再转换路径分隔符
                # input_dir = input_dir.replace('\\', '/')
                command.append("--input-directory")
                command.append(f"\"{ input_dir}\"")
        
        # 显存模式
        if self.data_model.get_bool('advanced', 'vram_enabled'):
            vram_mode = self.data_model.get_value('advanced', 'vram_mode', 'normal')
            if vram_mode == 'gpu_only':
                command.append("--gpu-only")
            elif vram_mode == 'high':
                command.append("--highvram")
            elif vram_mode == 'normal':
                command.append("--normalvram")
            elif vram_mode == 'low':
                command.append("--lowvram")
            elif vram_mode == 'no':
                command.append("--novram")
            elif vram_mode == 'cpu':
                command.append("--cpu")
        
        # 禁用元数据
        if self.data_model.get_bool('advanced', 'disable_metadata'):
            command.append("--disable-metadata")
        
        # 在命令末尾添加 & pause
        command.extend(["&", "pause"])
        
        return command
    
    def get_command_string(self):
        """获取当前启动参数的字符串表示"""
        command = self.build_command()
        # 跳过cmd.exe /c部分
        cmd_parts = command[2:]
        
        # 直接拼接剩余部分，保持和执行的一样
        cmd_str = " ".join(cmd_parts)
        
        return cmd_str
    
    def handle_stdout(self):
        """处理标准输出"""
        data = self.process.readAllStandardOutput()
        # 直接使用UTF-8解码，使用replace模式处理无法解码的字符
        stdout = bytes(data).decode('utf-8', errors='ignore')
        
        # 确保进度条数据不被截断，例如 [00:19<00:00, 77.05it/s]
        # 这里不做特殊处理，因为已在 startup_panel.py 的 _process_ansi_colors 方法中处理了 HTML 转义
        self.log_signal.emit(stdout)
        
        # 检查是否启用了重启命令接管
        if self.data_model.get_bool('advanced', 'restart_command_intercept_enabled', True):
            # 获取重启命令关键词
            restart_keyword = self.data_model.get_value('advanced', 'restart_command_keyword', 'Restarting...')
            
            # 检查输出中是否包含重启命令关键词
            if restart_keyword in stdout:
                self.log_signal.emit("\n检测到ComfyUI重启命令，正在由Manager接管重启过程...\n")
                
                # 设置标记，表示这是主动终止进程
                self._intentional_kill = True
                # 启用自动重启
                self._auto_restart = True
                
                # 停止当前进程
                self.stop_comfyui()
                
                # 等待进程完全停止
                if self.wait_for_finished(3000):
                    # 然后重新启动
                    self.start_comfyui()
                else:
                    # 如果等待超时，尝试强制终止
                    self.force_kill()
                    if self.wait_for_finished(3000):
                        self.start_comfyui()
    
    def handle_stderr(self):
        """处理标准错误"""
        data = self.process.readAllStandardError()
        # 使用与stdout相同的错误处理策略
        stderr = bytes(data).decode('utf-8', errors='ignore')
        self.log_signal.emit(stderr)
    
    def handle_error(self, error):
        """处理进程错误"""
        # 标记是否是主动终止进程
        is_intentional_kill = hasattr(self, '_intentional_kill') and self._intentional_kill
        
        # 如果是进程崩溃错误，但是是由于主动终止进程引起的，则不显示错误消息
        if error == QProcess.ProcessError.Crashed and is_intentional_kill:
            self.log_signal.emit("进程已终止")
            self.status_changed.emit(False)
            # 重置标记
            self._intentional_kill = False
            return
        
        error_messages = {
            QProcess.ProcessError.FailedToStart: "进程启动失败，请检查python_embeded/python.exe是否存在\n",
            QProcess.ProcessError.Crashed: "进程崩溃\n",
            QProcess.ProcessError.Timedout: "进程超时\n",
            QProcess.ProcessError.WriteError: "写入进程失败\n",
            QProcess.ProcessError.ReadError: "读取进程失败\n",
            QProcess.ProcessError.UnknownError: "未知错误\n"
        }
        
        error_msg = error_messages.get(error, "未知错误\n")
        self.log_signal.emit(f"错误: {error_msg}\n")
        self.error_occurred.emit(error_msg)
        self.status_changed.emit(False)
    
    def process_finished(self, exit_code, exit_status):
        """进程结束时调用"""
        # 无论是否主动终止，都发送状态变化信号
        self.status_changed.emit(False)
        print(f"进程结束，发送状态变化信号: False")
        
        # 检查是否是主动终止进程
        if not self._intentional_kill:
            # 只有在非主动终止的情况下才显示错误信息
            self.log_signal.emit(f"ComfyUI 进程终止，退出码: {exit_code}\n")
            
            # 如果是终止，尝试终止可能仍在运行的python.exe进程
            if self._python_pid is not None:
                try:
                    import subprocess
                    self.log_signal.emit(f"尝试清理残留的python.exe进程 (PID: {self._python_pid})\n")
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._python_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception as e:
                    self.log_signal.emit(f"清理残留进程时出错: {str(e)}\n")
            
            # 如果启用了自动重启，则尝试重启进程
            if self._auto_restart:
                self.log_signal.emit("ComfyUI 进程终止，正在尝试自动重启...\n")
                # 重置进程ID和标记
                self._current_pid = None
                self._python_pid = None
                self._intentional_kill = False
                
                # 等待一段时间，确保所有资源都被释放
                import time
                time.sleep(2)
                
                # 启动进程
                if self.start_comfyui():
                    self.log_signal.emit("ComfyUI 已自动重启\n")
                    return
                else:
                    self.log_signal.emit("ComfyUI 自动重启失败\n")
                    self.error_occurred.emit(f"ComfyUI 进程终止，退出码: {exit_code}，自动重启失败\n")
            else:
                self.error_occurred.emit(f"ComfyUI 进程终止，退出码: {exit_code}\n")
        else:
            # 主动终止进程，不显示错误信息
            self.log_signal.emit("ComfyUI 进程已正常终止\n")
            # 不发送错误信号，避免显示错误对话框
        
        # 发送状态变更信号
        self.status_changed.emit(False)
        
        # 重置进程ID和标记
        self._current_pid = None
        self._python_pid = None
        self._intentional_kill = False
    
    # 注意：is_running 和 wait_for_finished 方法已在类的前面定义
    
    def force_kill(self):
        """强制结束进程"""
        if self.process:
            # 设置_intentional_kill标记为True
            # 这样可以确保即使是通过force_kill方法终止进程，也不会显示崩溃错误
            self._intentional_kill = True
            # 禁用自动重启，因为这是用户主动强制终止
            self._auto_restart = False
            
            # 先尝试正常终止进程
            self.process.kill()
            
            import subprocess
            
            # 终止python.exe进程
            if self._python_pid is not None:
                try:
                    self.log_signal.emit(f"正在强制终止python.exe进程 (PID: {self._python_pid})\n")
                    # 使用进程ID终止python.exe进程及其子进程
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._python_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log_signal.emit(f"已强制终止python.exe进程 (PID: {self._python_pid})\n")
                except Exception as e:
                    self.log_signal.emit(f"强制终止python.exe进程时出错: {str(e)}\n")
            else:
                self.log_signal.emit("未找到python.exe进程ID，无法精确终止\n")
            
            # 终止cmd.exe进程
            cmd_pid = self._current_pid
            if cmd_pid is None:
                try:
                    cmd_pid = self.process.processId()
                    self.log_signal.emit(f"使用当前cmd.exe进程ID: {cmd_pid}\n")
                except Exception as e:
                    self.log_signal.emit(f"无法获取cmd.exe进程ID: {str(e)}\n")
            else:
                self.log_signal.emit(f"使用记录的cmd.exe进程ID: {cmd_pid}\n")
            
            # 如果有有效的cmd.exe进程ID，使用taskkill命令强制终止该进程及其所有子进程
            if cmd_pid is not None:
                try:
                    # 使用进程ID终止cmd.exe进程及其子进程
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(cmd_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log_signal.emit(f"已强制终止cmd.exe进程 (PID: {cmd_pid})及其所有子进程\n")
                except Exception as e:
                    self.log_signal.emit(f"强制终止cmd.exe进程时出错: {str(e)}\n")
            
            self.log_signal.emit("ComfyUI 进程已强制终止\n")
            # 发送状态变更信号
            self.status_changed.emit(False)
            # 重置进程ID
            self._current_pid = None
            self._python_pid = None
            # 清理额外python.exe进程的代码
            for pid in self._additional_python_pids:
                try:
                    self.log_signal.emit(f"尝试清理残留的额外python.exe进程 (PID: {pid})\n")
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception as e:
                    self.log_signal.emit(f"清理残留的额外进程时出错: {str(e)}\n")
            
            # 重置额外进程ID列表
            self._additional_python_pids = []
            return True
        return False