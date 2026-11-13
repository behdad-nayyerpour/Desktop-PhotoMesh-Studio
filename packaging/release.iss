#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef StageDir
  #error StageDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
[Setup]
AppId={{74DCCB58-21F5-4BB0-B93D-7DF3C76D64F5}
AppName=Lens2Mesh
AppVersion={#AppVersion}
AppPublisher=Behdad Nayyerpour
LicenseFile={#StageDir}\app\LICENSE
DefaultDirName={localappdata}\Programs\Lens2Mesh
DisableDirPage=no
DefaultGroupName=Lens2Mesh
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
SetupIconFile={#StageDir}\app\photomesh\resources\photomesh.ico
OutputDir={#OutputDir}
OutputBaseFilename=Lens2Mesh_Setup_{#AppVersion}
UninstallDisplayIcon={app}\app\photomesh\resources\photomesh.ico
Uninstallable=not PortableCheck
UsePreviousAppDir=not PortableCheck
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#StageDir}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#StageDir}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#StageDir}\tools\*"; DestDir: "{app}\tools"; Flags: recursesubdirs createallsubdirs ignoreversion
[InstallDelete]
Type: files; Name: "{autoprograms}\PhotoMesh Studio.lnk"; Check: not PortableCheck
Type: files; Name: "{autodesktop}\PhotoMesh Studio.lnk"; Check: not PortableCheck
Type: filesandordirs; Name: "{app}\app\photomesh"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\tools"

[Icons]
Name: "{autoprograms}\Lens2Mesh"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\photomesh\resources\photomesh.ico"; Check: not PortableCheck
Name: "{autodesktop}\Lens2Mesh"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\photomesh\resources\photomesh.ico"; Tasks: desktopicon; Check: not PortableCheck

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; Description: "Launch Lens2Mesh"; Flags: postinstall nowait skipifsilent

[Code]
function PortableCheck: Boolean;
begin
  Result := ExpandConstant('{param:portable|0}') = '1';
end;

