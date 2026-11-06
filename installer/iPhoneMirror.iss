; Установщик iPhone Mirror (Inno Setup 6).
; Собирается скриптом setup\build_installer.ps1 после setup\build_exe.ps1.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "iPhone Mirror"
#define AppExe "iPhone Mirror.exe"
#define SourceDir "..\dist\iPhone Mirror"
#define FirewallRule "iPhone Mirror (UxPlay)"
#define FirewallRuleUsb "iPhone Mirror (UxPlay, USB)"

[Setup]
AppId={{6F2C4B1E-8A7D-4E39-9C1B-5D7A2E4F8B31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=iPhone Mirror
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; По умолчанию — для всех пользователей (нужен админ, чтобы добавить правило брандмауэра),
; но можно выбрать установку только для себя.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=iPhoneMirror-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
LicenseFile=..\LICENSE
; ultra64 не помещается в память 32-битного ISCC — max + отдельный процесс сжатия.
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
russian.Firewall=Разрешить iPhone Mirror в брандмауэре Windows (частные сети и iPhone по USB)
english.Firewall=Allow iPhone Mirror through Windows Firewall (private networks and iPhone over USB)
russian.Launch=Запустить iPhone Mirror
english.Launch=Launch iPhone Mirror

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "firewall"; Description: "{cm:Firewall}"; Check: IsAdminInstallMode

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""{#FirewallRule}"" dir=in action=allow profile=private program=""{app}\_internal\uxplay\bin\uxplay.exe"" enable=yes"; \
  Flags: runhidden; Tasks: firewall
; Сеть iPhone по USB Windows обычно считает «общедоступной», поэтому отдельное
; правило: любой профиль, но только для подсети «Режима модема» iPhone.
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""{#FirewallRuleUsb}"" dir=in action=allow profile=any remoteip=172.20.10.0/28 program=""{app}\_internal\uxplay\bin\uxplay.exe"" enable=yes"; \
  Flags: runhidden; Tasks: firewall
Filename: "{app}\{#AppExe}"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM uxplay.exe"; Flags: runhidden; RunOnceId: "KillUxPlay"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#FirewallRule}"""; \
  Flags: runhidden; RunOnceId: "DelFirewall"; Check: IsAdminInstallMode
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#FirewallRuleUsb}"""; \
  Flags: runhidden; RunOnceId: "DelFirewallUsb"; Check: IsAdminInstallMode

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#AppName}"
