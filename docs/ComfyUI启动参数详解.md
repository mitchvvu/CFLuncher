ComfyUI 启动参数的详细解释
2025-02-21
1,526
阅读4分钟

介绍
ComfyUI 是一款基于 Stable Diffusion 的开源、可视化 AI 绘图工具，采用节点式图形用户界面（GUI），允许用户通过连接不同节点来构建复杂的图像生成工作流

启动参数
以下是 ComfyUI 启动参数的详细解释，按功能分类整理：

1. 网络与服务相关
--listen [IP]
设置 ComfyUI 监听的 IP 地址。默认为 127.0.0.1（仅本地访问）。可以设置为 0.0.0.0 或 ::（监听所有 IPv4 和 IPv6 地址）以允许外部访问。
--port PORT
设置 ComfyUI 的监听端口。
--tls-keyfile TLS_KEYFILE 和 --tls-certfile TLS_CERTFILE
启用 TLS（SSL）加密，使 ComfyUI 可以通过 https:// 访问。需要同时提供密钥文件和证书文件。
--enable-cors-header [ORIGIN]
启用跨域资源共享（CORS），允许指定的来源（或默认的 *）访问 ComfyUI。
--max-upload-size MAX_UPLOAD_SIZE
设置允许的最大上传文件大小（单位：MB）。
--auto-launch 和 --disable-auto-launch
自动在默认浏览器中打开 ComfyUI 界面（默认启用）。--disable-auto-launch 用于禁用此功能。
--dont-print-server
不打印服务器输出日志。
--windows-standalone-build
为 Windows 独立安装包启用一些便捷功能（如自动打开页面）。
--multi-user
启用多用户模式，为每个用户单独存储数据。
--enable-compress-response-body
启用响应体压缩，减少网络传输数据量。
2. 目录与文件相关
--base-directory BASE_DIRECTORY
设置 ComfyUI 的基础目录，用于存放模型、自定义节点、输入、输出和临时文件。
--extra-model-paths-config PATH [PATH ...]
加载额外的模型路径配置文件（extra_model_paths.yaml）。
--output-directory OUTPUT_DIRECTORY
设置 ComfyUI 的输出目录，覆盖基础目录中的输出路径。
--temp-directory TEMP_DIRECTORY
设置 ComfyUI 的临时文件目录，覆盖基础目录中的临时路径。
--input-directory INPUT_DIRECTORY
设置 ComfyUI 的输入文件目录，覆盖基础目录中的输入路径。
--user-directory USER_DIRECTORY
设置 ComfyUI 的用户目录，覆盖基础目录。
3. GPU/CUDA 相关
--cuda-device DEVICE_ID
指定使用的 CUDA 设备 ID。

--cuda-malloc 和 --disable-cuda-malloc
启用或禁用 CUDA 异步内存分配（默认启用）。禁用时会回退到传统内存分配方式。

--force-fp32 和 --force-fp16
强制使用 FP32 或 FP16 精度进行计算。

--fp32-unet、--fp16-unet、--bf16-unet 等
设置 UNet 模型的精度（如 FP32、FP16、BF16 等）。

--fp16-vae、--fp32-vae、--bf16-vae、--cpu-vae
设置 VAE 的精度或运行设备（如 FP16、FP32、BF16 或 CPU）。

--fp16-text-enc、--fp32-text-enc 等
设置文本编码器的精度。

--force-channels-last
强制模型在推理时使用通道后置格式。

--directml [DIRECTML_DEVICE]
使用 PyTorch DirectML（适用于 Windows 的 DirectML 后端）。

--oneapi-device-selector SELECTOR_STRING
设置 Intel oneAPI 设备选择器。

--disable-ipex-optimize
禁用 Intel PyTorch 扩展的优化功能。

--gpu-only、--highvram、--normalvram、--lowvram、--novram、--cpu
控制模型的存储位置和显存使用策略：

--gpu-only：所有模型都存储在 GPU 上。
--highvram：模型在 GPU 上保持加载状态。
--normalvram：正常显存使用模式。
--lowvram：将 UNet 分割为多个部分以节省显存。
--novram：当 --lowvram 仍显存不足时使用。
--cpu：所有计算都在 CPU 上完成（速度较慢）。
--reserve-vram RESERVE_VRAM
预留一定量的显存（单位：GB），供操作系统或其他软件使用。

4. 性能与优化相关
--preview-method [none,auto,latent2rgb,taesd]
设置采样节点的默认预览方法。

--preview-size PREVIEW_SIZE
设置采样节点的最大预览尺寸。

--cache-classic 和 --cache-lru CACHE_LRU
设置缓存策略：

--cache-classic：使用旧版缓存策略。
--cache-lru：使用 LRU 缓存策略，可指定最大缓存节点结果数量。
--use-split-cross-attention、--use-quad-cross-attention、--use-pytorch-cross-attention、--use-sage-attention
设置不同的交叉注意力优化策略。

--disable-xformers
禁用 xformers（一种高效的 Transformer 实现）。

--force-upcast-attention 和 --dont-upcast-attention
强制启用或禁用注意力机制的上浮精度。

--disable-smart-memory
禁用智能内存管理（强制将模型卸载到常规 RAM）。

--deterministic
强制 PyTorch 使用确定性算法（可能影响性能）。

--fast
启用一些未经测试且可能影响质量的优化。

--disable-metadata
禁用在输出文件中保存提示元数据。

--disable-all-custom-nodes
禁用所有自定义节点。

5. 日志与调试相关
--verbose [{DEBUG,INFO,WARNING,ERROR,CRITICAL}]
设置日志级别。
--log-stdout
将正常进程输出发送到标准输出（stdout）而不是标准错误（stderr）。
6. 前端与界面相关
--front-end-version FRONT_END_VERSION
指定前端版本（需要联网从 GitHub 下载）。
--front-end-root FRONT_END_ROOT
指定本地前端目录路径，覆盖前端版本设置。
7. 其他
--default-hashing-function {md5,sha1,sha256,sha512}
设置用于比较文件名或内容的哈希函数，默认为 sha256。
--quick-test-for-ci
用于 CI 测试的快速模式。