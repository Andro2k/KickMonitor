; Script corregido para KickMonitor
; Asegúrate de haber compilado antes con: 
; pyinstaller ... --name "KickMonitor" ...

#define MyAppName "KickMonitor"
#define MyAppVersion "1.7"
#define MyAppPublisher "TheAndro2K"
#define MyAppExeName "KickMonitor.exe"

[Setup]
; Genera un GUID nuevo en Inno Setup (Tools > Generate GUID) y pégalo aquí
AppId={{GENERA-TU-PROPIO-GUID-AQUI}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
CloseApplications=yes
RestartApplications=no

; Configuración de Salida
OutputDir=installer
OutputBaseFilename=KickMonitor_Setup_v1.7
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Permisos de Administrador (Para instalar en Archivos de Programa)
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

; --- PERSONALIZACIÓN VISUAL (Opcional) ---
; Si no tienes estas imágenes en 'assets', comenta estas líneas con ;
WizardImageFile=assets\install_bg.bmp
WizardSmallImageFile=assets\install_small.bmp
WizardImageStretch=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; El ejecutable principal desde la carpeta dist
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; --- LIMPIEZA AL DESINSTALAR (NUEVO) ---
; Esto asegura que si borran la app, también se borre la base de datos de AppData
[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"