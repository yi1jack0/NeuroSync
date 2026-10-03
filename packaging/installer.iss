; Inno Setup 6.3+ script. Build:  ISCC.exe /DAppVersion=0.1.0 packaging\installer.iss
; Expects the PyInstaller output in ..\dist\NeuroSync (see build_windows.ps1).
#define AppName "NeuroSync Studio"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{B7C1E5D2-4A6F-4E3B-9C0D-5E2A8F1D7A31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=NeuroSync
; Per-user install by default (no admin prompt); the dialog lets users choose all-users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\NeuroSync Studio
DisableProgramGroupPage=yes
DefaultGroupName={#AppName}
OutputDir=..\dist-installer
OutputBaseFilename=NeuroSync-Setup-{#AppVersion}
SetupIconFile=neurosync.ico
UninstallDisplayIcon={app}\NeuroSync.exe
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; A running tray instance would lock its files during upgrade: ask it to close.
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\NeuroSync\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\NeuroSync.exe"; AppUserModelID: "NeuroSync.Studio"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\NeuroSync.exe"; Tasks: desktopicon; AppUserModelID: "NeuroSync.Studio"

[Run]
Filename: "{app}\NeuroSync.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
// User data (presets, settings) lives in %APPDATA%\NeuroSync and survives upgrades.
// On a manual uninstall we ask; silent uninstalls always keep it.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\NeuroSync');
    if DirExists(DataDir) and (not UninstallSilent) then
      if MsgBox('Also remove your saved presets and settings?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
