#define AppName "AI-Stalker"
#define AppVersion "0.1.0"
#define AppPublisher "Blacklisted Binary Labs"
#define AppExeName "AIStalker.exe"

[Setup]
AppId={{DA44B5DF-6B6F-4E3F-86E3-1BAF1F9A593C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\AI-Stalker
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=AI-Stalker-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x86 x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "service"; Description: "Install as a Windows Service (runs in background)"; Flags: unchecked
Name: "failsafe"; Description: "Configure as Failsafe Node (standby takeover mode)"; Flags: unchecked
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: unchecked

[Files]
Source: "dist\\AIStalker-x64.exe"; DestDir: "{app}"; DestName: "{#AppExeName}"; Check: Is64BitInstallMode
Source: "dist\\AIStalker-x86.exe"; DestDir: "{app}"; DestName: "{#AppExeName}"; Check: not Is64BitInstallMode
Source: "dist\\README.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{autoprograms}\\AI-Stalker"; Filename: "{app}\\{#AppExeName}"
Name: "{autodesktop}\\AI-Stalker"; Filename: "{app}\\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#AppExeName}"; Description: "Launch AI-Stalker"; Flags: nowait postinstall skipifsilent
Filename: "{sys}\\sc.exe"; Parameters: "create \"AIStalker\" binPath= \"{app}\\{#AppExeName} --service\" start= auto"; Tasks: service; Flags: runhidden
Filename: "{sys}\\sc.exe"; Parameters: "description \"AIStalker\" \"AI-Stalker Background Service\""; Tasks: service; Flags: runhidden
Filename: "{app}\\{#AppExeName}"; Parameters: "--configure --role failsafe --failover-minutes {code:GetFailoverMinutes}"; Tasks: failsafe; Flags: runhidden

[UninstallRun]
Filename: "{sys}\\sc.exe"; Parameters: "stop \"AIStalker\""; Tasks: service; Flags: runhidden
Filename: "{sys}\\sc.exe"; Parameters: "delete \"AIStalker\""; Tasks: service; Flags: runhidden

[Code]
var
  FailoverMinutesPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  FailoverMinutesPage := CreateInputQueryPage(
    wpSelectTasks,
    'Failover Settings',
    'Configure standby activation delay',
    'Choose how long a node should wait after the primary goes offline before it takes over.'
  );
  FailoverMinutesPage.Add('Failover delay (minutes, 1-60):', False);
  FailoverMinutesPage.Values[0] := '5';
end;

function GetFailoverMinutes(Param: string): string;
begin
  if WizardIsTaskSelected('failsafe') then
    Result := FailoverMinutesPage.Values[0]
  else
    Result := '5';
end;
