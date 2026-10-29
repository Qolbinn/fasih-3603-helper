; ==============================================================================
; INNO SETUP SCRIPT - FASIH 3603 HELPER (BPS KABUPATEN TANGERANG)
; ==============================================================================
; Skrip ini menghasilkan file installer mandiri: FASIH_3603_Helper_Setup_vX.X.exe
; Cukup ubah MyAppVersion di bawah saat ada rilis versi baru.

#define MyAppName "FASIH 3603 Helper"
#define MyAppVersion "1.8.0"
#define MyAppPublisher "BPS Kabupaten Tangerang"
#define MyAppURL "https://tangerangkab.bps.go.id"
#define MyAppExeName "FASIH_3603_Helper.exe"
#define MyAppId "{{BPS3603-FASIH-HELPER-2026}}"

[Setup]
; Identitas aplikasi (AppId tetap sama antar-versi agar update otomatis menimpa versi lama)
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Lokasi instalasi di AppData Pengguna (bebas hak Administrator, cocok untuk PC dinas kantor)
DefaultDirName={localappdata}\Programs\FASIH 3603 Helper
DisableProgramGroupPage=yes

; Output file otomatis mengikuti nomor versi
OutputDir=..\dist_installer
OutputBaseFilename=FASIH_3603_Helper_Setup_v{#MyAppVersion}

; Pengaturan kompresi maksimal & tema modern
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Ikon Installer & Tampilan di Add/Remove Programs (Control Panel)
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\assets\app_icon.ico

; Izin instalasi fleksibel tanpa hak admin khusus
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Menyalin seluruh berkas hasil build PyInstaller dari folder dist
Source: "..\dist\FASIH_3603_Helper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Shortcut di Menu Start
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; AppUserModelID: "bps3603.fasihhelper.desktop"
; Shortcut di Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon; AppUserModelID: "bps3603.fasihhelper.desktop"

[Run]
; Opsi langsung jalankan aplikasi setelah instalasi selesai
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
