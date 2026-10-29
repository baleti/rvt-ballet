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
