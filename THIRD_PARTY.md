# 第三方组件与许可

Zsharp 的本体代码（`app_qt.py`、构建脚本、界面资源）以 GPL-3.0 发布。

程序在**运行时**通过子进程调用下列第三方可执行文件，并通过 PyInstaller 把它们一起打包进发行版。
这些组件**不修改源码**，各自保留其原始许可。再分发本软件时，以下条款同时生效。

---

## 1. PyQt5 / Qt 5 — GPL-3.0 或 商业许可

- 版权：Riverbank Computing Limited；Qt 版权：The Qt Company
- 许可：**GPL v3**（本仓库使用的方式）或 Riverbank 商业许可
- 主页：https://www.riverbankcomputing.com/software/pyqt/
- 说明：这是本项目必须采用 GPL-3.0 的原因。PyQt5 以 GPL 分发时，链接它的应用整体需遵循 GPL。

> Qt 本体另有 LGPL-3.0 授权路径，但 PyQt5 绑定本身是 GPL / 商业双许可。

## 2. FFmpeg — GPL

- 许可：**GPL v2 或更高**（本项目附带的是含 GPL 组件的构建）
- 主页：https://ffmpeg.org/
- 本项目使用的 Windows 构建来源：https://github.com/GyanD/codexffmpeg
- **本项目使用的构建**：`ffmpeg 9.0.2-essentials_build-www.gyan.dev`，
  配置含 `--enable-gpl --enable-version3`，即 **GPL v3**
- **再分发义务（已履行）**：发行版内 `licenses/FFmpeg-SOURCE.txt` 写明了精确版本、
  完整 configure 参数、源码仓库地址与书面索取方式；`licenses/GPL-3.0.txt` 为许可全文。
- 源码地址：https://github.com/GyanD/codexffmpeg

## 3. ncnn — BSD-3-Clause

- 版权：Tencent
- 许可：BSD-3-Clause
- 主页：https://github.com/Tencent/ncnn
- 说明：各 `*-ncnn-vulkan.exe` 推理引擎的底层运行时。

## 4. Real-ESRGAN — BSD-3-Clause

- 版权：Xintao Wang 等（XPixelGroup）
- 许可：BSD-3-Clause
- 主页：https://github.com/xinntao/Real-ESRGAN
- 本项目使用的可执行封装：https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan

## 5. Real-CUGAN — MIT

- 主页：https://github.com/nihui/realcugan-ncnn-vulkan
- 模型版权归原作者，使用前请阅读上游说明。

## 6. waifu2x — MIT

- 原始算法：https://github.com/nagadomi/waifu2x
- 本项目使用的封装：https://github.com/nihui/waifu2x-ncnn-vulkan

## 7. RealSR — 见上游

- 主页：https://github.com/nihui/realsr-ncnn-vulkan
- 模型（DF2K / DF2K_JPEG）版权归原作者。
- **注意**：该组件的具体许可条款请以仓库内 `LICENSE` 与上游 README 为准，本项目未做二次声明。

## 8. RIFE — MIT

- 主页：https://github.com/nihui/rife-ncnn-vulkan
- 模型：`rife-anime`、`rife-v4.6`

## 9. libVLC — LGPL-2.1+

- 版权：VideoLAN
- 主页：https://www.videolan.org/vlc/libvlc.html
- 说明：以 DLL 形式动态调用，未修改源码，符合 LGPL 动态链接要求。

## 10. mpv / libmpv — GPL-2.0+ 或 LGPL-2.1+

- 主页：https://mpv.io/
- 说明：具体许可取决于所使用的构建选项，请核对发行版内 `mpv/` 目录附带的信息。

---

## 字体与图标

界面字体使用系统自带字体（微软雅黑 / Segoe UI），未嵌入分发。
`icon.png`、`icon.ico`、`ic_*.png` 为本项目自制资源，随本项目一同以 GPL-3.0 发布。

---

## 许可文本位置

所有第三方许可原文集中放在仓库的 [`licenses/`](licenses/) 目录，构建时会自动复制进发行版。
对应关系见 [`licenses/README.md`](licenses/README.md)。

---

## 再分发检查清单

发布新版本前请逐项确认：

- [x] `licenses/GPL-3.0.txt` 为 FFmpeg 与 PyQt5 的许可全文
- [x] `licenses/FFmpeg-SOURCE.txt` 给出 FFmpeg 源码获取方式（GPL 第 3 节义务）
- [x] 各引擎的 MIT / BSD-3 许可文本均已收录
- [ ] 若替换了任一引擎版本，同步更新 `licenses/` 与本文档中的版本、链接
- [ ] 发行说明中不得声称模型权重为自研（均为上游开源权重）
- [ ] 生成 SHA256 校验值并附在 Release 里
