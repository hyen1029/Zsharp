# Zsharp

> **本地运行的 AI 画质增强工具** —— 图片 / 视频超分，2× / 3× / 4×。
> 全程离线，不联网、不上传、不依赖任何云服务。

![platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078D4)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![qt](https://img.shields.io/badge/GUI-PyQt5-41CD52)
![license](https://img.shields.io/badge/license-GPL--3.0-blue)

---

## 这是什么

Zsharp 是一个 Windows 桌面端的**本地 AI 超分工具**。把低清、模糊、有压缩痕迹的图片或视频拖进窗口，它会在你自己的显卡上跑 Real-ESRGAN / Real-CUGAN / RealSR / waifu2x 等模型，输出 2×、3× 或 4× 的高清版本。

所有计算都在本机完成：**没有云端、没有账号、没有上传**。断网也能正常使用。

- 图片：`png` `jpg` `jpeg` `bmp` `tif` `tiff` `webp`
- 视频：`mp4` `mkv` `avi` `mov` `wmv` `flv` `m4v` `ts` `webm`

---

## 特性

| | |
|---|---|
| 🖼 **图片超分** | 单张或整批处理，支持拖拽文件夹递归扫描 |
| 🎬 **视频超分** | 自动「拆帧 → 逐帧增强 → 合成」，**保留原音轨** |
| 🧠 **4 套引擎 / 10 个模型** | 动漫、真人、实拍、老番各有对应模型 |
| 🎞 **AI 补帧** | 内置 RIFE，可对视频做动漫 / 通用两套补帧模型 |
| 🎚 **画面调整** | 对比度 / 饱和度 / 锐化 / 亮度，图片与视频共用一套参数 |
| 🔍 **分割对比** | 左原图 / 右超分，中间分割线可拖动，改完立刻看差别 |
| ⚡ **硬件编码自适应** | 自动识别显卡，优先 NVENC / AMF / QSV，失败回落 libx264 |
| 🖱 **拖拽即用** | 拖图片自动切到图片页，拖视频自动切到视频页 |
| 🔒 **完全离线** | 不联网、不上传、无遥测 |
| 🎨 **磨砂玻璃界面** | 深色主题，可调主色、背景模糊与压暗 |

---

## 引擎与模型

| 引擎 | 模型 | 适合 | 倍率 | 降噪 |
|---|---|---|---|---|
| **Real-ESRGAN** | 动漫 / 视频 · 快速 | 二次元、CG、游戏截图、视频首选 | 2× / 3× / 4× | — |
| | 动漫 · 高质量 | 线条更干净，慢约 3 倍 | 4× | — |
| | 真人 / 实拍 | 真实照片、风景 | 4× | — |
| **Real-CUGAN** | 动漫 · 均衡（SE） | 细节与降噪平衡 | 2× / 3× / 4× | -1 ~ 3 |
| | 动漫 · 强力（Pro） | 压缩痕迹重的老图、老番 | 2× / 3× | -1 / 0 / 3 |
| **RealSR** | 真人 / 实拍 · 高保真（DF2K） | 实拍最稳，不油腻 | 4× | — |
| | 真人 / 实拍 · 去 JPEG 脏边 | 压烂的网图先用它 | 4× | — |
| **waifu2x** | 动漫 · 降噪（CUNet） | 老动画、包浆图 | 1× / 2× | 0 ~ 3 |
| | 动漫 · 快速（Upconv） | 追求速度 | 1× / 2× | 0 ~ 3 |
| | 真人 · 快速（Photo） | 真人照片的轻量选择 | 1× / 2× | 0 ~ 3 |

> 推理后端统一为 **ncnn-Vulkan**，A 卡 / N 卡 / 核显都能跑。

---

## 安装

### 方式一：安装包（推荐）

从 [Releases](https://github.com/hyen1029/Zsharp/releases) 下载 `Zsharp-Setup-x.y.z.exe`，双击安装。

- 默认装到 `%LOCALAPPDATA%\Programs\Zsharp`，**不需要管理员权限**
- 支持自定义安装目录、创建桌面快捷方式、干净卸载

### 方式二：绿色版

下载 `Zsharp-x.y.z-win64.zip`，解压到任意目录，双击 `Zsharp.exe`。

> ⚠️ 必须解压后再运行，**不要**在压缩包内直接双击 —— 程序需要在同级目录读写 `bin/`、`output/` 和 `settings.json`。

### 系统要求

| 项 | 要求 |
|---|---|
| 系统 | Windows 10 / 11（64 位） |
| 显卡 | 支持 Vulkan 的独显或核显（NVIDIA / AMD / Intel 均可） |
| 内存 | 建议 16 GB 以上（4× 视频处理更吃内存） |
| 磁盘 | 安装约 600 MB；视频处理需额外约「视频体积 ×10」的临时空间 |

---

## 使用

1. 双击 `Zsharp.exe`
2. 切到「图片超分」或「视频超分」
3. 把文件（或整个文件夹）拖进窗口，也可以点「添加」
4. 左侧选模型和倍数，需要时调「画面调整」
5. 点右下「开始处理」
6. 结果在各标签页的输出目录，文件名带 `_2x` / `_4x`

完整说明见 [docs/使用说明.md](docs/使用说明.md)。

---

## 画面调整

超分模型的输出有时会偏灰、偏闷，这一组参数就是用来找回来的：

| 参数 | 默认值 | 建议 |
|---|---|---|
| 对比度 | 1.06 | 嫌灰就加到 1.10 ~ 1.15 |
| 饱和度 | 1.08 | 画面发闷就加 |
| 锐化 | 0.60 | 模糊重加到 0.8 ~ 1.0；噪点多降到 0.3 |
| 亮度 | 0 | 一般不用动 |

这组参数图片和视频都生效，视频在编码时一并处理，**不会多跑一遍**。点「恢复默认」一键还原。

---

## 选型建议

| 素材 | 推荐 |
|---|---|
| 动漫 / 游戏 CG | Real-ESRGAN 快速，或 Real-CUGAN 均衡 |
| 老番、压缩痕迹重 | Real-CUGAN Pro（降噪 3） |
| 真人照片 | Real-ESRGAN「真人 / 实拍」，或 waifu2x Photo |
| 实拍视频 | RealSR（DF2K），最稳 |
| 只降噪不放大 | waifu2x，倍数设 1 |
| 视频 | 先 2 倍，4 倍约需 3 倍时间 |

---

## 性能参考

测试环境：AMD RX 7650 GRE，Windows 11。

| 任务 | 耗时 |
|---|---|
| 图片 1080p → 4×（Real-ESRGAN 快速） | 约 2 秒 |
| 视频 640×480 → 2×（7.5 秒片段） | 约 15 秒 |
| 视频 1080p → 2× | 约「时长 × 2 ~ 4」 |

---

## 常见问题

| 现象 | 处理 |
|---|---|
| 处理到一半报错 | 切块改 256；视频先换 2 倍 |
| 视频没有声音 | 默认保留原音轨，个别编码需先转 AAC |
| 画面偏「塑料」 | 换模型，或把倍数降到 2 |
| 画面发灰 | 对比度调到 1.10 以上，锐化 0.6 左右 |
| 拖进去没反应 | 确认扩展名在支持列表里；文件夹会递归扫描 |

---

## 技术栈

- **GUI**：PyQt5（自绘磨砂玻璃控件、无边框窗口、自定义标题栏）
- **推理**：ncnn-Vulkan 可执行文件，通过 `subprocess` 调用
- **视频**：FFmpeg（拆帧 / 合成 / 编码 / 音轨复用）
- **补帧**：RIFE（ncnn-Vulkan）
- **打包**：PyInstaller（onedir）+ Inno Setup

---

## 从源码构建

```powershell
# 1. 环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 准备运行时依赖（ffmpeg、各引擎 exe、模型权重）
#    下载地址见 docs/构建与发布.md，放到 bin/ 下

# 3. 直接运行
python app_qt.py

# 4. 打包
.\build\build.ps1
```

详见 [docs/构建与发布.md](docs/构建与发布.md)。

---

## 目录结构

```
Zsharp/
├── app_qt.py              # 主程序（单文件，约 2700 行）
├── icon.png / icon.ico    # 应用图标
├── ic_play.png 等          # 播放控件图标
├── requirements.txt
├── build/
│   ├── Zsharp.spec        # PyInstaller 配置
│   └── build.ps1          # 一键打包脚本
├── installer/
│   └── setup.iss          # Inno Setup 安装包脚本
├── scripts/
│   └── fetch-bin.ps1      # 拉取运行时依赖
├── docs/
│   ├── 使用说明.md
│   └── 构建与发布.md
├── licenses/              # 第三方许可文本（随发行版分发）
│   ├── README.md          # 组件与许可对应关系
│   ├── FFmpeg-SOURCE.txt  # FFmpeg 源码获取声明（GPL 义务）
│   └── *.txt
├── bin/                   # 运行时依赖（不进仓库，见 .gitignore）
└── output/                # 默认输出目录
```

---

## 第三方组件

本项目**不包含**任何第三方组件的源码，仅在运行时调用它们。所有许可原文收录在
[`licenses/`](licenses/)，并随发行版一同分发，详见 [THIRD_PARTY.md](THIRD_PARTY.md)。

- **FFmpeg** 为 GPL v3 构建，`licenses/FFmpeg-SOURCE.txt` 提供了对应源码的获取方式
- **PyQt5** 为 GPL-3.0 / 商业双许可 —— 这是本项目采用 GPL-3.0 的原因
- **Real-ESRGAN / Real-CUGAN / waifu2x / RealSR / RIFE** 的模型权重均为上游开源权重，
  版权归各自作者，本项目仅做集成调用

---

## 许可证

本项目以 **[GPL-3.0](LICENSE)** 发布。

之所以是 GPL-3.0 而不是 MIT：本程序基于 **PyQt5** 构建，而 PyQt5 是 *GPL v3 / 商业* 双许可。
按 GPL 分发 PyQt5 应用时，整个程序需以 GPL 兼容条款开放 —— 这与仓库里同样采用
GPL 的 FFmpeg 构建也一致。

> 如果你持有 [Riverbank 商业许可](https://www.riverbankcomputing.com/commercial/license-faq)，
> 或把 GUI 迁移到 LGPL 的 PySide6，则可以把本项目改为 MIT / Apache-2.0 等宽松许可。

第三方组件各自遵循其原始许可，详见 [THIRD_PARTY.md](THIRD_PARTY.md)。

---

## 免责声明

本工具仅供个人学习与合法的画质修复用途。使用者应确保对所处理的内容拥有合法权利。
软件按「现状」提供，不附带任何明示或暗示的担保。

---

## English

**Zsharp** is a fully offline AI upscaler for Windows — 2× / 3× / 4× for both **images and videos**.
It wraps Real-ESRGAN, Real-CUGAN, RealSR and waifu2x (ncnn-Vulkan) in a PyQt5 desktop UI, with RIFE frame interpolation and FFmpeg-based video assembly. Nothing leaves your machine.

- Drag & drop files or folders
- Left/right split comparison with a draggable divider
- Auto GPU detection with NVENC / AMF / QSV hardware encoding
- 4 engines, 10 models, 1× to 4×
- Windows 10/11 x64, requires a Vulkan-capable GPU

Build from source: `pip install -r requirements.txt`, drop the engine binaries into `bin/`, then `python app_qt.py`.

Licensed under **GPL-3.0** (required by the GPL-licensed PyQt5 binding).
Third-party notices in [THIRD_PARTY.md](THIRD_PARTY.md).
