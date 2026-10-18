; Inno Setup script for bitComposer on Windows: the player (bitComposer.exe,
; with libopenmpt bundled inside), the command line (bitcomposer-cli.exe),
; a Start menu entry and an uninstaller. Built by .github/workflows/windows.yml
; with the version passed in from the package.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{9D1D5E6A-2B4C-4A8E-9F3B-bitComposer01}
AppName=bitComposer
AppVersion={#AppVersion}
AppPublisher=CatDogBark
AppPublisherURL=https://github.com/CatDogBark/bitComposer
AppSupportURL=https://github.com/CatDogBark/bitComposer/issues
DefaultDirName={autopf}\bitComposer
DefaultGroupName=bitComposer
UninstallDisplayIcon={app}\bitComposer.exe
; Paths below are relative to the repository root, not to this script.
SourceDir=..\..
OutputDir=.
OutputBaseFilename=bitComposer-setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Files]
Source: "dist\bitComposer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\bitcomposer-cli.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "pkg\README-WINDOWS.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\bitComposer"; Filename: "{app}\bitComposer.exe"
Name: "{group}\bitComposer command line"; Filename: "{cmd}"; Parameters: "/k ""{app}\bitcomposer-cli.exe"" --help"; WorkingDir: "{app}"
Name: "{group}\Uninstall bitComposer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\bitComposer"; Filename: "{app}\bitComposer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\bitComposer.exe"; Description: "Start bitComposer"; Flags: nowait postinstall skipifsilent
