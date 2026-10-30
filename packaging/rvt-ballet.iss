; Inno Setup script: per-user install (no admin), Start menu entry, "Open with rvt-ballet" for .rvt (not the default handler).
#define AppName "rvt-ballet"
#define AppVersion "0.1.0"
[Setup]
AppId={{2B7C4D90-83A1-4F6E-B1D2-5E9A0C7F1D42}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename={#AppName}-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ChangesAssociations=yes
SetupIconFile=rvt-ballet.ico
UninstallDisplayIcon={app}\rvt-ballet.ico
UninstallDisplayName={#AppName}
[Files]
Source: "rvt-ballet.ico"; DestDir: "{app}"
Source: "..\dist\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs createallsubdirs
Source: "..\dist\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs
[UninstallDelete]
Type: filesandordirs; Name: "{app}"
[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; IconFilename: "{app}\rvt-ballet.ico"; Parameters: "-m rvtballet serve"; WorkingDir: "{app}\app"
[Registry]
Root: HKCU; Subkey: "Software\Classes\rvt-ballet.rvt\DefaultIcon"; ValueType: string; ValueData: "{app}\rvt-ballet.ico"
Root: HKCU; Subkey: "Software\Classes\rvt-ballet.rvt"; ValueType: string; ValueData: "Revit model"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\rvt-ballet.rvt\shell\open\command"; ValueType: string; ValueData: """{app}\python\pythonw.exe"" -m rvtballet open ""%1"""
Root: HKCU; Subkey: "Software\Classes\.rvt\OpenWithProgids"; ValueType: string; ValueName: "rvt-ballet.rvt"; ValueData: ""; Flags: uninsdeletevalue
[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: "-m rvtballet serve"; WorkingDir: "{app}\app"; Description: "Start rvt-ballet"; Flags: postinstall nowait skipifsilent unchecked

[Code]
// The app is a windowless pythonw.exe: Restart Manager cannot ask it to close, so a silent upgrade/uninstall over a running copy failed (exit 5).
// Stop only processes whose image lives under the install folder. Runs in InitializeSetup because the Restart Manager check aborts before PrepareToInstall.
procedure StopAppProcesses(Dir: String);
var rc: Integer; Ps: String;
begin
  Log('stopping processes under ' + Dir);
  // 32-bit setup on 64-bit Windows would get the 32-bit PowerShell (WOW64), which cannot read the Path of 64-bit processes
  if IsWin64 then Ps := ExpandConstant('{sysnative}\WindowsPowerShell\v1.0\powershell.exe') else Ps := 'powershell.exe';
  Exec(Ps, '-NoProfile -ExecutionPolicy Bypass -Command "$a=''' + Dir + '''; $m=Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($a, [StringComparison]::OrdinalIgnoreCase) }; $m | Stop-Process -Force; Start-Sleep -Milliseconds 800"', '', SW_HIDE, ewWaitUntilTerminated, rc);
  Log('stop rc=' + IntToStr(rc));
end;

function InitializeSetup(): Boolean;
var Dir: String;
begin
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{2B7C4D90-83A1-4F6E-B1D2-5E9A0C7F1D42}_is1', 'Inno Setup: App Path', Dir) then
    Dir := ExpandConstant('{localappdata}\Programs\rvt-ballet');
  if DirExists(Dir) then StopAppProcesses(Dir);
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  StopAppProcesses(ExpandConstant('{app}'));
  Result := True;
end;
