[Setup]
AppId={{B5A7F0E0-1234-5678-9ABC-DEF012345678}}
AppName=SyncSentinel
AppVersion=0.9.0
AppPublisher=SyncSentinel Development
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={pf}\SyncSentinel
DefaultGroupName=SyncSentinel
OutputDir=installers
OutputBaseFilename=SyncSentinel-0.9.0-Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=syncsentinel_icon.ico
UninstallDisplayIcon={app}\syncsentinel_icon.ico
UninstallDisplayName=SyncSentinel v0.9.0
VersionInfoVersion=0.9.0
VersionInfoProductVersion=0.9.0
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create Start Menu icon"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SyncSentinel-0.9.0.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "syncsentinel_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "syncsentinel_icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SyncSentinel"; Filename: "{app}\SyncSentinel-0.9.0.exe"; IconFilename: "{app}\syncsentinel_icon.ico"; Tasks: startmenuicon
Name: "{commondesktop}\SyncSentinel"; Filename: "{app}\SyncSentinel-0.9.0.exe"; IconFilename: "{app}\syncsentinel_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\SyncSentinel-0.9.0.exe"; Description: "{cm:LaunchProgram,SyncSentinel}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Prompt to remove user data
    if MsgBox('Do you want to remove user data and settings (including credentials and config from AppData\Roaming\SyncSentinel)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UserDataPath := ExpandConstant('{userappdata}\SyncSentinel');
      if DirExists(UserDataPath) then
      begin
        DelTree(UserDataPath, True, True, True);
      end;
    end;
  end;
end;
