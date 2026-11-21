# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.5.1] — 2026-11-21

首个开源版本。

### 功能
- 图片超分：`png` `jpg` `jpeg` `bmp` `tif` `tiff` `webp`，支持批量与文件夹递归
- 视频超分：`mp4` `mkv` `avi` `mov` `wmv` `flv` `m4v` `ts` `webm`，拆帧 → 增强 → 合成，保留原音轨
- 4 套引擎 / 10 个模型：Real-ESRGAN、Real-CUGAN、RealSR、waifu2x（ncnn-Vulkan）
- RIFE 补帧：`rife-anime` / `rife-v4.6`，另支持 FFmpeg 光流补帧
- 画面调整：对比度 / 饱和度 / 锐化 / 亮度，图片与视频共用
- 左右分割对比视图，分割线可拖动
- 图片预览支持滚轮缩放与拖拽平移
- 显卡自动识别，编码器自动选择 NVENC / AMF / QSV，失败回落 libx264
- 拖拽文件或文件夹入窗，按类型自动切换图片 / 视频页
- 磨砂玻璃深色界面，可调主色、背景模糊、背景压暗
- 设置持久化到 `settings.json`
- 内置更新检查（`UPDATE_URL` 默认为空）

### 打包
- PyInstaller `onedir` 布局，`_internal/` 存放依赖
- Inno Setup 安装包：安装至 `%LOCALAPPDATA%\Programs\Zsharp`，无需管理员权限

---

## 待补充

`1.5.1` 之前的历史版本未纳入本仓库。若需要保留，请在此处按版本倒序补齐。
