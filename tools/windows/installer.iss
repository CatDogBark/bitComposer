; Inno Setup script for bitComposer on Windows: the player's folder build
; (bitComposer.exe with Qt and libopenmpt beside it in _internal), the command
; line (bitcomposer-cli.exe), a Start menu entry and an uninstaller. Built by
; .github/workflows/windows.yml with the version passed in from the package.
;
; Installs for the current user by default (no administrator prompt, and the
; player's UPDATE button can run the next installer quietly); the first
; page offers all users instead, and an update keeps whichever was chosen.
; UPDATE runs this with /SILENT /SUPPRESSMSGBOXES /NORESTART
; /CLOSEAPPLICATIONS /RELAUNCH=1: a progress bar, then the player again.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{9D1D5E6A-2B4C-4A8E-9F3B-bitComposer01}
AppName=bitComposer
AppVersion={#AppVersion}
AppPublisher=CatDogBark
AppCopyright=Copyright (c) 2026 Enlightened Solutions LLC
AppContact=catdogbark@pm.me
AppPublisherURL=https://github.com/CatDogBark/bitComposer
AppSupportURL=https://github.com/CatDogBark/bitComposer/issues
DefaultDirName={autopf}\bitComposer
DefaultGroupName=bitComposer
UninstallDisplayIcon={app}\bitComposer.exe
SetupIconFile=build\bitcomposer.ico
; Paths below are relative to the repository root, not to this script.
SourceDir=..\..
OutputDir=.
OutputBaseFilename=bitComposer-setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
; The Run value above is per user by design, in either install mode.
UsedUserAreasWarning=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Registry]
; Start at login is the player's own setting (its per-user Run value); the
; installer never writes it, the uninstaller takes it out.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "bitComposer"; ValueType: none; Flags: uninsdeletevalue dontcreatekey

[InstallDelete]
; The bundle's file set changes between versions (Qt's in particular): clear
; the old one rather than leave stale libraries beside the new.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\bitComposer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\bitComposer"; Filename: "{app}\bitComposer.exe"
Name: "{group}\bitComposer command line"; Filename: "{cmd}"; Parameters: "/k ""{app}\bitcomposer-cli.exe"" --help"; WorkingDir: "{app}"
Name: "{group}\Uninstall bitComposer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\bitComposer"; Filename: "{app}\bitComposer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\bitComposer.exe"; Description: "Start bitComposer"; Flags: nowait postinstall skipifsilent
Filename: "{app}\bitComposer.exe"; Flags: nowait; Check: Relaunch

[Code]
// The player's UPDATE button asks for the player back after a quiet install;
// any other silent install (a script, a package manager) does not get one.
function Relaunch: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:RELAUNCH|0}') = '1');
end;
