#define MyAppName "AGCN Live Voice"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AGCN"
#define MyAppExeName "AGCN Live Voice.exe"

[Setup]
AppId={{A9A9A2F2-4B8F-4F1D-9C0E-A6C120260929}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AGCN Live Voice
DefaultGroupName=AGCN Live Voice
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=AGCN-Live-Voice-Setup
Compression=lzma2/max
SolidCompression=yes
DiskSpanning=yes
DiskSliceSize=1800000000
SlicesPerDisk=1
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=AGCN Live Voice - apresentador inteligente para LIVE
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\AGCN Live Voice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AGCN Live Voice"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AGCN Live Voice"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir AGCN Live Voice"; Flags: nowait postinstall skipifsilent
