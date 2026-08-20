; Inno Setup script for the Flooring Partners QR Code Generator.
; Compile with:  iscc build\installer.iss
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)

#define AppName        "QR Code Generator"
; CI passes /DAppVersion=x.y.z; the fallback keeps local builds working.
#ifndef AppVersion
  #define AppVersion   "2.1.2"
#endif
#define AppPublisher   "Flooring Partners"
#define AppExeName     "FPQRGenerator.exe"

[Setup]
; AppId is the identity Windows uses to recognise an upgrade. NEVER change it
; between releases, or every version installs side by side instead of replacing
; the previous one.
AppId={{0234F8BE-94D5-4A96-8387-A0CB5A5DAD1B}

AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppPublisher} {#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}

; Per-user install into %LOCALAPPDATA%\Programs. This is the important choice:
; it means updates need no admin rights, so the in-app updater can run silently
; without a UAC prompt. Switch to "admin" + {autopf} only if IT deploys this
; centrally and you drop the self-updater in favour of Intune/GPO.
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppPublisher}\{#AppName}
DefaultGroupName={#AppPublisher}
DisableProgramGroupPage=yes

OutputDir=..\dist\installer
OutputBaseFilename=FPQRGenerator-{#AppVersion}-setup
SetupIconFile=..\src\fp.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppPublisher} {#AppName}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

; Shut down a running copy so its files can be replaced, instead of demanding
; a reboot. This is what makes silent self-update work reliably.
CloseApplications=yes
RestartApplications=no
CloseApplicationsFilter=*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; The whole PyInstaller onedir output. recursesubdirs picks up _internal\.
Source: "..\dist\FPQRGenerator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Interactive install: offer a checkbox on the Finished page.
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

; Silent install: relaunch automatically. A silent run is almost always the
; self-updater, and the user was using the program a moment ago, so dropping
; them back into it is the expected behaviour. Pass /NORELAUNCH to suppress
; this for unattended deployment (see the Check function below).
Filename: "{app}\{#AppExeName}"; Flags: nowait; Check: ShouldRelaunch

[UninstallDelete]
; Remove the generated config on uninstall. Drop this section if you would
; rather preserve user settings across an uninstall/reinstall cycle.
Type: filesandordirs; Name: "{localappdata}\{#AppPublisher}\{#AppName}"

[Code]
const
  { "Shell Folders" holds already-expanded paths, so redirected or OneDrive-
    backed locations resolve correctly. Reading the profile path and appending
    "Favorites" would miss those. }
  ShellFoldersKey = 'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders';

function ShellFolder(const ValueName: String): String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, ShellFoldersKey, ValueName, Result) then
    Result := '';
end;

function IsUnder(const Child, Parent: String): Boolean;
var
  P: String;
begin
  Result := False;
  if Parent = '' then
    Exit;
  P := AddBackslash(Lowercase(Parent));
  Result := Copy(AddBackslash(Lowercase(Child)), 1, Length(P)) = P;
end;

{ Returns the friendly name of the protected folder Dir sits inside, or an
  empty string. These are Microsoft Defender's default Controlled folder access
  locations. Installing into one makes the program an untrusted binary living
  inside the area Defender guards: SmartScreen fires repeatedly, the program
  cannot write files, and the uninstaller cannot remove its own files, so
  Settings -> Apps fails to uninstall it. }
function ProtectedFolderName(const Dir: String): String;
begin
  Result := '';
  if IsUnder(Dir, ShellFolder('Personal')) then
    Result := 'Documents'
  else if IsUnder(Dir, ShellFolder('My Pictures')) then
    Result := 'Pictures'
  else if IsUnder(Dir, ShellFolder('My Music')) then
    Result := 'Music'
  else if IsUnder(Dir, ShellFolder('My Video')) then
    Result := 'Videos'
  else if IsUnder(Dir, ShellFolder('Desktop')) then
    Result := 'Desktop'
  else if IsUnder(Dir, ShellFolder('Favorites')) then
    Result := 'Favorites';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FolderName: String;
begin
  Result := True;

  { WizardSilent is excluded deliberately. NextButtonClick also runs on silent
    installs, and returning False there makes Setup exit with no message - which
    would break the self-updater for anyone who already has a bad install,
    leaving them stuck with no way to see why. }
  if (CurPageID = wpSelectDir) and not WizardSilent then
  begin
    FolderName := ProtectedFolderName(WizardDirValue);
    if FolderName <> '' then
    begin
      MsgBox('This program cannot be installed inside your ' + FolderName + ' folder.'
        + #13#10#13#10
        + 'Windows ransomware protection guards that folder, which would stop the '
        + 'program saving files, cause repeated security warnings, and prevent it '
        + 'from being uninstalled afterwards.'
        + #13#10#13#10
        + 'Please choose a different folder, or click Back and accept the default.',
        mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function ShouldRelaunch: Boolean;
var
  I: Integer;
begin
  { Only silent installs reach here; interactive ones use the Finished page. }
  Result := WizardSilent;
  if Result then
    for I := 1 to ParamCount do
      if CompareText(ParamStr(I), '/NORELAUNCH') = 0 then
      begin
        Result := False;
        Exit;
      end;
end;
