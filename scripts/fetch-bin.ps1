<#
.SYNOPSIS
    检查 bin/ 运行时依赖是否齐全，并打印缺失项的下载地址。

.DESCRIPTION
    Zsharp 通过子进程调用 bin/ 下的推理引擎与 FFmpeg。
    这些二进制体积很大（约 760 MB），不纳入 Git 仓库，需要单独准备。

    本脚本只做「检查 + 指引」，不会自动下载 —— 各上游的发行包结构、
    版本号和许可声明需要你自己确认后再放入 bin/。

.PARAMETER OpenPages
    同时用默认浏览器打开所有缺失组件的发布页。

.EXAMPLE
    .\scripts\fetch-bin.ps1
    .\scripts\fetch-bin.ps1 -OpenPages
#>

[CmdletBinding()]
param(
    [switch]$OpenPages
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bin  = Join-Path $Root "bin"

# 组件定义：名称 / 需要匹配的文件名 / 上游发布页 / 说明
$Components = @(
    @{ Name = "FFmpeg";        Exe = "ffmpeg.exe";                     Url = "https://github.com/GyanD/codexffmpeg/releases";            Note = "GPL 构建；保留 LICENSE 与 COPYING.GPLv*" }
    @{ Name = "Real-ESRGAN";   Exe = "realesrgan-ncnn-vulkan.exe";     Url = "https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases"; Note = "需连同 models/ 一起放入" }
    @{ Name = "Real-CUGAN";    Exe = "realcugan-ncnn-vulkan.exe";      Url = "https://github.com/nihui/realcugan-ncnn-vulkan/releases";   Note = "需 models-se/ 与 models-pro/" }
    @{ Name = "RealSR";        Exe = "realsr-ncnn-vulkan.exe";         Url = "https://github.com/nihui/realsr-ncnn-vulkan/releases";      Note = "需 models-DF2K/ 与 models-DF2K_JPEG/" }
    @{ Name = "waifu2x";       Exe = "waifu2x-ncnn-vulkan.exe";        Url = "https://github.com/nihui/waifu2x-ncnn-vulkan/releases";     Note = "需 models-cunet/ 等" }
    @{ Name = "RIFE";          Exe = "rife-ncnn-vulkan.exe";           Url = "https://github.com/nihui/rife-ncnn-vulkan/releases";        Note = "补帧用；需 rife-anime/ 与 rife-v4.6/" }
    @{ Name = "libVLC";        Exe = "libvlc.dll";                     Url = "https://www.videolan.org/vlc/download-windows.html";        Note = "可选：视频预览" }
    @{ Name = "libmpv";        Exe = "libmpv-2.dll";                   Url = "https://mpv.io/installation/";                              Note = "可选：视频预览" }
)

Write-Host "== Zsharp 运行时依赖检查 ==" -ForegroundColor Cyan
Write-Host "bin/ 目录: $Bin`n"

if (-not (Test-Path $Bin)) {
    New-Item -ItemType Directory -Path $Bin | Out-Null
    Write-Host "已创建空的 bin/ 目录。`n" -ForegroundColor Yellow
}

# 递归索引 bin/ 下所有文件，避免逐项重复遍历
$found = @{}
Get-ChildItem $Bin -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    $found[$_.Name.ToLower()] = $_.FullName
}

$missing = @()

foreach ($c in $Components) {
    $hit = $found[$c.Exe.ToLower()]
    if ($hit) {
        $rel = $hit.Substring($Bin.Length).TrimStart('\')
        Write-Host ("  [OK]   {0,-12} {1}" -f $c.Name, $rel) -ForegroundColor Green
    }
    else {
        Write-Host ("  [缺失] {0,-12} {1}" -f $c.Name, $c.Note) -ForegroundColor Red
        $missing += $c
    }
}

Write-Host ""

if ($missing.Count -eq 0) {
    Write-Host "全部依赖已就绪，可以直接运行 python app_qt.py 或开始打包。" -ForegroundColor Green
    exit 0
}

Write-Host "缺少 $($missing.Count) 个组件。下载地址：" -ForegroundColor Yellow
foreach ($c in $missing) {
    Write-Host ""
    Write-Host "  $($c.Name)" -ForegroundColor White
    Write-Host "    $($c.Url)"
    Write-Host "    $($c.Note)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "放置约定见 docs/构建与发布.md 第 2 节。" -ForegroundColor DarkGray

if ($OpenPages) {
    foreach ($c in $missing) { Start-Process $c.Url }
    Write-Host "`n已在浏览器中打开上述页面。" -ForegroundColor Cyan
}
