; Installateur Windows de Newton Fractals (Inno Setup 6)
;
; Construit par packaging/construire.py, après PyInstaller :
;   ISCC.exe /DVersion=1.1.0 packaging\installateur.iss
; Entrée : dist\NewtonFractals\   Sortie : dist\NewtonFractals-Setup-<version>.exe
;
; Installation par utilisateur par défaut (aucun droit administrateur demandé) ;
; l'utilisateur peut choisir une installation pour tous dans la boîte de dialogue.

#ifndef Version
  #define Version "0.0.0"
#endif
#define Nom "Newton Fractals"
#define Exe "NewtonFractals.exe"

[Setup]
AppId={{8C1F3B52-6E7A-4D0B-9F43-2A5D7C9E1B60}
AppName={#Nom}
AppVersion={#Version}
AppVerName={#Nom} {#Version}
AppPublisher=Elliot Galaor
AppPublisherURL=https://github.com/ElliotGalaor/Newton_Fractals
AppSupportURL=https://github.com/ElliotGalaor/Newton_Fractals/issues
AppUpdatesURL=https://github.com/ElliotGalaor/Newton_Fractals/releases
VersionInfoVersion={#Version}
DefaultDirName={autopf}\{#Nom}
DefaultGroupName={#Nom}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SourceDir=..
OutputDir=dist
OutputBaseFilename=NewtonFractals-Setup-{#Version}
SetupIconFile=packaging\icone.ico
UninstallDisplayIcon={app}\{#Exe}
UninstallDisplayName={#Nom}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
fr.Manuel=Manuel d'utilisation
en.Manuel=User manual
fr.Desinstaller=Désinstaller {#Nom}
en.Desinstaller=Uninstall {#Nom}

[Tasks]
Name: "bureau"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Mise à jour : le contenu de _internal (Python, Qt, modules) et du moteur change d'une version
; à l'autre ; on efface l'ancien pour ne pas mélanger les fichiers de deux versions
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\moteur"

[Files]
Source: "dist\NewtonFractals\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nom}"; Filename: "{app}\{#Exe}"
Name: "{group}\{cm:Manuel}"; Filename: "{app}\manuel\index.html"
Name: "{group}\{cm:Desinstaller}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nom}"; Filename: "{app}\{#Exe}"; Tasks: bureau

[Run]
Filename: "{app}\{#Exe}"; Description: "{cm:LaunchProgram,{#Nom}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\manuel\index.html"; Description: "{cm:Manuel}"; Flags: shellexec nowait postinstall skipifsilent unchecked

