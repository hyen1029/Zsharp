# 一键打包：PyInstaller 生成 onedir，再把 bin/ 与界面资源复制进去
# 用法（仓库根目录）：.\build\build.ps1
#           可选：.\build\build.ps1 -WithPreview   （额外打包 mpv / vlc 预览组件，+258 MB）

param(
    [switch]$WithPreview
)

$ErrorActionPreference = "Stop"

$Root      = Split-Path -Parent $PSScriptRoot
$Dist      = Join-Path $Root "dist\Zsharp"
$BinSrc    = Join-Path $Root "bin"

Write-Host "== Zsharp 打包 ==" -ForegroundColor Cyan
Write-Host "仓库根目录: $Root"

# --- 1. 依赖检查 ---------------------------------------------------------
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "未找到 python，请先安装 Python 3.9~3.11 并加入 PATH。" }

& python -c "import PyQt5, PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "缺少依赖，请先执行：pip install -r requirements.txt"
}

if (-not (Test-Path $BinSrc)) {
    Write-Warning "未找到 bin/ 目录。打包会成功，但生成的程序没有推理引擎，无法处理文件。"
    Write-Warning "请参考 docs/构建与发布.md 第 2 节准备运行时依赖。"
}

# --- 2. 清理 -------------------------------------------------------------
Write-Host "`n[1/4] 清理旧产物 ..." -ForegroundColor Yellow
foreach ($d in @("build\work", "dist")) {
    $p = Join-Path $Root $d
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}

# --- 3. PyInstaller ------------------------------------------------------
Write-Host "`n[2/4] 运行 PyInstaller ..." -ForegroundColor Yellow
Push-Location $Root
try {
    & pyinstaller "build\Zsharp.spec" --noconfirm --clean `
        --workpath "build\work" --distpath "dist"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败，退出码 $LASTEXITCODE" }
}
finally { Pop-Location }

if (-not (Test-Path (Join-Path $Dist "Zsharp.exe"))) {
    throw "打包后未找到 dist\Zsharp\Zsharp.exe"
}

# --- 4. 复制 bin 与资源 --------------------------------------------------
Write-Host "`n[3/4] 复制 bin/ 与界面资源 ..." -ForegroundColor Yellow

if (Test-Path $BinSrc) {
    Write-Host "  复制 bin/ (可能较慢，约 760 MB)"
    Copy-Item $BinSrc -Destination $Dist -Recurse -Force

    # 可选预览组件，官方发行版默认不打包（省约 258 MB）
    # 需要视频预览时把 -WithPreview 加上
    if (-not $WithPreview) {
        foreach ($d in @("mpv", "vlc")) {
            $p = Join-Path $Dist "bin\$d"
            if (Test-Path $p) {
                Remove-Item $p -Recurse -Force
                Write-Host "  已排除可选组件 bin\$d"
            }
        }
    }
}

foreach ($f in @("icon.png", "ic_play.png", "ic_pause.png", "ic_replay.png", "使用说明.txt")) {
    $src = Join-Path $Root $f
    if (Test-Path $src) { Copy-Item $src -Destination $Dist -Force }
}

# 同步 docs 里的使用说明（若存在）
$docUsage = Join-Path $Root "docs\使用说明.md"
if (Test-Path $docUsage) { Copy-Item $docUsage -Destination $Dist -Force }

# 第三方许可文本必须随发行版分发（GPL / BSD / MIT 的硬性义务）
$licSrc = Join-Path $Root "licenses"
if (Test-Path $licSrc) {
    Copy-Item $licSrc -Destination $Dist -Recurse -Force
    Write-Host "  已复制 licenses/（第三方许可文本）"
}
else {
    Write-Warning "缺少 licenses/ 目录！发行版将不满足 GPL/BSD/MIT 的许可随附义务。"
}

# 根目录 LICENSE 也要进发行版
$rootLic = Join-Path $Root "LICENSE"
if (Test-Path $rootLic) { Copy-Item $rootLic -Destination $Dist -Force }

# --- 5. 汇总 -------------------------------------------------------------
$size = (Get-ChildItem $Dist -Recurse -File | Measure-Object Length -Sum).Sum
Write-Host "`n[4/4] 完成" -ForegroundColor Green
Write-Host "  产物目录: $Dist"
Write-Host ("  总大小  : {0:N1} MB" -f ($size / 1MB))
Write-Host "`n下一步：编译安装包 -> installer\setup.iss"
