# 贡献指南

感谢你愿意改进 Zsharp。以下是参与方式。

## 报告问题

提 issue 前请先搜索是否已有同类问题。新建 issue 时请附上：

- 操作系统版本（如 Windows 11 23H2）
- 显卡型号与驱动版本
- 所选引擎、模型、倍数、降噪档位
- 输入素材的分辨率与格式
- **完整报错信息**或截图（可从「设置 → 通用」查看版本号）

> 请勿上传包含隐私内容的原始素材。复现问题时请使用可公开的样例文件。

## 提交代码

```powershell
git clone https://github.com/hyen1029/Zsharp.git
cd Zsharp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app_qt.py
```

开发时把引擎可执行文件放到 `bin/` 下（目录结构见 [docs/构建与发布.md](docs/构建与发布.md)），
否则程序启动后大部分功能不可用。

### 代码约定

- 单文件主程序 `app_qt.py` 目前**有意保持单文件**，便于 PyInstaller 打包与分发；
  拆分模块的改动请先开 issue 讨论。
- 4 空格缩进，UTF-8 编码，行尾 LF。
- 新增引擎或模型时，同步更新 `ENGINES` 字典、`README.md` 的模型表、`THIRD_PARTY.md`。
- 提交信息用中文或英文均可，建议遵循 `feat:` / `fix:` / `docs:` / `refactor:` 前缀。

### 分支与 PR

- 从 `main` 切出功能分支：`feat/xxx`、`fix/xxx`
- 一个 PR 只做一件事；改动界面请附截图或录屏
- PR 描述里说明「改了什么 / 为什么 / 怎么验证」

## 许可

本项目以 GPL-3.0 发布。提交 PR 即表示你同意以同一许可授权你的贡献。
请勿引入与 GPL-3.0 不兼容的代码或资源。
