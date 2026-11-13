#ifndef AddonStage
  #error AddonStage is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef RuntimeFolder
  #error RuntimeFolder is required
#endif
#ifndef AddonRevision
  #error AddonRevision is required
#endif
[Setup]
AppId={{4683EF83-5152-455B-9563-8F2D436C227B}
AppName=Lens2Mesh Neural GPU Add-on
AppVersion=1.0.5
AppPublisher=Behdad Nayyerpour
DefaultDirName={code:GetBaseDir}
DisableDirPage=no
AppendDefaultDirName=no
UsePreviousAppDir=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=no
CreateUninstallRegKey=no
CreateAppDir=yes
DirExistsWarning=no
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
LicenseFile={#AddonStage}\addon-license.txt
OutputDir={#OutputDir}
OutputBaseFilename=Lens2Mesh_NeuralGPU_Addon_1.0.5

[Files]
Source: "{#RuntimeFolder}\*"; DestDir: "{tmp}\Lens2MeshGpuPayload\app\photomesh\resources\neural-cuda12"; Flags: ignoreversion deleteafterinstall
Source: "{#AddonStage}\packaging\*"; DestDir: "{tmp}\Lens2MeshGpuPayload\packaging"; Flags: ignoreversion deleteafterinstall

[Code]
function GetBaseDir(Param: String): String;
begin
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{74DCCB58-21F5-4BB0-B93D-7DF3C76D64F5}_is1', 'InstallLocation', Result) then
    Result := ExpandConstant('{localappdata}\Programs\Lens2Mesh');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not FileExists(ExpandConstant('{app}\python\python.exe')) or
     not FileExists(ExpandConstant('{app}\app\runtime.id')) or
     not FileExists(ExpandConstant('{app}\app\photomesh\__init__.py')) then
    Result := 'Install Lens2Mesh 1.0.5 first, then select its installation folder. Close Lens2Mesh before adding GPU support.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  Params, LogPath: String;
  Details: AnsiString;
begin
  if CurStep = ssPostInstall then begin
    LogPath := ExpandConstant('{tmp}\Lens2MeshGpuPayload\install.log');
    Params := '"' + ExpandConstant('{tmp}\Lens2MeshGpuPayload\packaging\neural_addon.py') +
      '" --root "' + ExpandConstant('{app}') + '" --payload "' +
      ExpandConstant('{tmp}\Lens2MeshGpuPayload') + '" --revision {#AddonRevision} --log "' + LogPath + '"';
    if not Exec(ExpandConstant('{app}\python\python.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, Code) or (Code <> 0) then begin
      Details := '';
      LoadStringFromFile(LogPath, Details);
      RaiseException('GPU add-on was not installed. Close Lens2Mesh and verify the selected folder.' + #13#10 + String(Details));
    end;
  end;
end;
