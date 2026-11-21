; Zsharp 安装包脚本 · Inno Setup 6
; 编译：ISCC.exe installer\setup.iss
;
; 路径相对于本文件所在目录（installer\），因此无需改动即可在任意机器上编译。
; 依赖 ..\dist\Zsharp\ 由 build\build.ps1 生成。

#define AppName        "Zsharp"
#define AppVer         "1.5.1"
#define Publisher      "hyen1029"
#define AppURL         "https://github.com/hyen1029/Zsharp"
#define SourceDir      "..\dist\Zsharp"
#define OutputDir      "..\release"

[Setup]
; 升级识别用，保持不变则新版本可覆盖安装；一旦发布就不要再改
AppId={{8E2A2C1B-4E77-4C63-9C21-7A3E0D5B9F11}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer}
AppPublisher={#Publisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; 安装到用户目录，不需要管理员权限
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-Setup-{#AppVer}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppName}.exe
UninstallDisplayName={#AppName}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0

LicenseFile=..\LICENSE

[Languages]
Name: "cn"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; 主程序与全部运行时依赖（含 bin/ 下的引擎与模型）
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppName}.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}";     Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 用户配置与输出目录不自动删除（避免误删处理结果），仅清理临时目录
Type: filesandordirs; Name: "{tmp}\zsharp_qt"

[Code]
// 安装前检查磁盘空间：完整包约 700 MB
function InitializeSetup(): Boolean;
var
  FreeMB, TotalMB: Cardinal;
begin
  Result := True;
  if GetSpaceOnDisk(ExpandConstant('{localappdata}'), True, FreeMB, TotalMB) then
  begin
    if FreeMB < 1200 then
    begin
      if MsgBox('可用磁盘空间不足 1.2 GB，安装后可能无法正常处理视频。' + #13#10 +
                '仍要继续吗？', mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;
