# 第三方许可文本

本目录收录 Zsharp 运行时依赖的全部第三方许可原文。**发行版中这些文件随程序一同分发**，
请勿删除。

## 对应关系

| 组件 | 发行位置 | 许可 | 本目录文件 |
|---|---|---|---|
| **FFmpeg** | `bin/ffmpeg/ffmpeg.exe` | **GPL-3.0** | `GPL-3.0.txt`、`FFmpeg-SOURCE.txt` |
| **ncnn**（推理运行时） | 各 `*-ncnn-vulkan.exe` 内静态链接 | BSD-3-Clause | `ncnn-BSD-3.txt` |
| **Real-ESRGAN**（ncnn-vulkan 版） | `bin/realesrgan/` | MIT | `Real-ESRGAN-ncnn-MIT.txt` |
| **Real-ESRGAN**（原项目，模型来源） | 模型权重 | BSD-3-Clause | `Real-ESRGAN-BSD-3.txt` |
| **Real-CUGAN** | `bin/realcugan/` | MIT | `Real-CUGAN-MIT.txt` |
| **RealSR** | `bin/realsr/` | MIT | `RealSR-LICENSE.txt` |
| **waifu2x** | `bin/waifu2x/` | MIT | `waifu2x-MIT.txt` |
| **RIFE** | `bin/rife/` | MIT | `RIFE-MIT.txt` |
| **libmpv / mpv** | `bin/mpvlib/libmpv-2.dll` | GPL-2.0-or-later | `mpv-COPYING.txt` |
| **libVLC**（可选，默认不打包） | `bin/vlc/` | LGPL-2.1-or-later | `LGPL-2.1.txt` |
| **PyQt5 / Qt 5** | `_internal/PyQt5/` | **GPL-3.0** | `GPL-3.0.txt` |

## 关键义务

### FFmpeg（GPL-3.0）

以 GPL 分发二进制时，必须同时提供**对应源码的获取方式**。
`FFmpeg-SOURCE.txt` 列出了本项目所用构建的精确版本与源码地址，**必须随发行版一同提供**。

### PyQt5（GPL-3.0）

PyQt5 是 GPL-3.0 / 商业双许可。以 GPL 方式分发时，链接它的应用（即 Zsharp 本体）
整体需遵循 GPL-3.0 —— 这就是本仓库采用 GPL-3.0 的原因。

### BSD-3 / MIT

要求保留版权声明与许可文本。本目录已完整收录，随安装包分发即视为满足。

## 维护

替换任一引擎版本时：

1. 重新下载对应上游的 `LICENSE`，覆盖本目录同名文件
2. 更新 `THIRD_PARTY.md` 中的版本与链接
3. 检查 `FFmpeg-SOURCE.txt` 里的版本号是否仍与实际二进制一致

核对实际二进制版本：

```powershell
.\bin\ffmpeg\ffmpeg.exe -version
.\bin\realesrgan\realesrgan-ncnn-vulkan.exe -h
```
