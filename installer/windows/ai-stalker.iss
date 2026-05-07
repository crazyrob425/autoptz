#define AppName "AI-Stalker"
#define AppVersion "0.1.0"
#define AppPublisher "Blacklisted Binary Labs"
#define AppExeName "AIStalker.exe"
#define ServiceName "AIStalkerService"
#define ServiceDisplayName "AI-Stalker Background Service"

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
Name: "service"; Description: "Install as a Windows Service (requires service-capable build)"; Flags: unchecked
Name: "failsafe"; Description: "Configure as Failsafe Node (requires failsafe-capable build)"; Flags: unchecked
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
Filename: "{sys}\\sc.exe"; Parameters: "create \"{#ServiceName}\" binPath= \"{app}\\{#AppExeName} --service\" start= auto"; Tasks: service; Flags: runhidden; Check: ShouldInstallService
Filename: "{sys}\\sc.exe"; Parameters: "description \"{#ServiceName}\" \"{#ServiceDisplayName}\""; Tasks: service; Flags: runhidden; Check: ShouldInstallService

[UninstallRun]
Filename: "{sys}\\sc.exe"; Parameters: "stop \"{#ServiceName}\""; Tasks: service; Flags: runhidden; Check: AppSupportsService
Filename: "{sys}\\sc.exe"; Parameters: "delete \"{#ServiceName}\""; Tasks: service; Flags: runhidden; Check: AppSupportsService

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

function AppSupportsService: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\\AIStalker.service-capable'));
end;

function AppSupportsFailsafe: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\\AIStalker.failsafe-capable'));
end;

function ShouldInstallService: Boolean;
begin
  Result := WizardIsTaskSelected('service') and AppSupportsService;
end;

function GetFailoverMinutes(Param: string): string;
var
  Minutes: Integer;
begin
  if WizardIsTaskSelected('failsafe') then
    Minutes := StrToIntDef(FailoverMinutesPage.Values[0], 5)
  else
    Minutes := 5;

  if Minutes < 1 then
    Minutes := 1;
  if Minutes > 60 then
    Minutes := 60;

  Result := IntToStr(Minutes);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  FailsafeConfigPath: string;
  FailsafeConfigBody: string;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('service') and not AppSupportsService then
      MsgBox('Service mode was selected, but this build is not service-capable yet.', mbInformation, MB_OK);
    if WizardIsTaskSelected('failsafe') then
    begin
      FailsafeConfigPath := ExpandConstant('{app}\\failsafe.pending.ini');
      FailsafeConfigBody := '[failsafe]' + #13#10 +
        'enabled=true' + #13#10 +
        'takeover_delay_minutes=' + GetFailoverMinutes('') + #13#10 +
        'status=pending_app_support';
      SaveStringToFile(FailsafeConfigPath, FailsafeConfigBody, False);

      if not AppSupportsFailsafe then
        MsgBox('Failsafe mode was selected. A pending config file was created and will activate automatically once a failsafe-capable build is installed.', mbInformation, MB_OK);
    end;
  end;
end;
