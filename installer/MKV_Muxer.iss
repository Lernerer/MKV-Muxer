; Inno Setup script for MKV Muxer 1.0
; Компиляция: ISCC.exe installer\MKV_Muxer.iss
; Требуется Inno Setup 6.3+ (проверено на 7.1.1).
; Установка per-user, без прав администратора.

#define MyAppName "MKV Muxer"
#define MyAppVersion "1.0"
#define MyAppPublisher "MKV Muxer contributors"
#define MyAppExeName "MKV_Muxer.exe"
#define MyAppId "{{BBBF3421-38FC-49B6-9A2A-9B523E4593DF}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\MKV Muxer
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=MKV_Muxer_{#MyAppVersion}_setup
SetupIconFile=..\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
LicenseFile=..\LICENSES\GPL-2.0.txt

; --- Подпись (см. SIGNING.md) ---
; 1) Настройте Tools -> Configure Sign Tools: имя "signtool",
;    команда: "C:\...\signtool.exe" sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f
; 2) Раскомментируйте строки ниже:
;SignTool=signtool
;SignedUninstaller=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\MKV_Muxer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\mkv_muxer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSES\*"; DestDir: "{app}\LICENSES"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Лицензии {#MyAppName}"; Filename: "{app}\LICENSES"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
