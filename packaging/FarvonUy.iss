; ═══════════════════════════════════════════════════════════════════
;  Farvon Uy — Inno Setup 6
;  Natija:  installer\FarvonUySetup.exe   <- foydalanuvchiga shu beriladi
; ═══════════════════════════════════════════════════════════════════

#define Nom       "Farvon Uy"
#define Versiya   "1.2.1"
#define Muallif   "Farvon Uy"
#define ExeNom    "FarvonUy.exe"

[Setup]
AppId={{9C4E1A72-5F3B-4D8E-9A61-0C7B2E5D4A18}
AppName={#Nom}
AppVersion={#Versiya}
AppVerName={#Nom} {#Versiya}
AppPublisher={#Muallif}
DefaultDirName={autopf}\FarvonUy
DefaultGroupName={#Nom}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=..\installer
OutputBaseFilename=FarvonUySetup
SetupIconFile=..\assets\farvonuy.ico
UninstallDisplayIcon={app}\{#ExeNom}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "uz"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ish stolida yorliq yaratilsin"; \
    GroupDescription: "Qo'shimcha:"

; Eski o'rnatishdan qolgan fayllarni tozalaymiz. Busiz PyInstaller
; papkasida eski .pyd/.dll qolib ketadi va dastur tushunarsiz xato beradi.
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\PySide6"
Type: files;          Name: "{app}\*.pyd"
Type: files;          Name: "{app}\*.dll"

[Files]
Source: "..\dist\FarvonUy\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nom}"; Filename: "{app}\{#ExeNom}"
Name: "{group}\{#Nom}ni o'chirish"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nom}"; Filename: "{app}\{#ExeNom}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeNom}"; \
    Description: "{#Nom} dasturini ochish"; \
    Flags: nowait postinstall skipifsilent

; Ma'lumotlar bazasi %LOCALAPPDATA%\FarvonUy ichida — dastur o'chirilsa
; ham TEGILMAYDI. Odamning pul tarixini o'chirib yuborish mumkin emas.
[UninstallDelete]
Type: dirifempty; Name: "{app}"
