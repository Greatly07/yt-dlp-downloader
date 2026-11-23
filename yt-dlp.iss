[Setup]
AppName=yt-dlp Media Downloader
AppVersion=2.0.0
VersionInfoVersion=2.0.0
OutputDir=.
SetupIconFile=yt-dlp.ico
UninstallDisplayIcon={app}\yt_dlp_app.exe
; Installs to User AppData/Programs so "Update yt-dlp Now", on-demand FFmpeg/Node downloads, and settings.json don't require Admin rights
DefaultDirName={autopf}\yt-dlp Downloader
PrivilegesRequired=lowest
OutputBaseFilename=yt-dlp_Downloader_Setup
Compression=lzma2
SolidCompression=yes

[Types]
Name: "full"; Description: "Full installation (Recommended — includes FFmpeg & Node.js)"
Name: "minimal"; Description: "Minimal installation (yt-dlp only — skip FFmpeg & Node.js)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "core"; Description: "yt-dlp Media Downloader & yt-dlp Engine (Required)"; Types: full minimal custom; Flags: fixed
Name: "ffmpeg"; Description: "FFmpeg & FFprobe (Required for audio conversion, cover art, video merging, time clips & preview)"; Types: full custom
Name: "nodejs"; Description: "Node.js Runtime (Recommended to prevent YouTube bot blocks / HTTP 403 errors)"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "songpulse"; Description: "Register 'ytdlp://' protocol for automatic SongPulse playlist batch downloads"; GroupDescription: "Integrations:"

[Files]
Source: "yt_dlp_app.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "yt-dlp.ico"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "C:\ffmpeg\bin\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: ffmpeg
Source: "C:\ffmpeg\bin\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: ffmpeg
Source: "C:\Program Files\nodejs\node.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: nodejs

[Registry]
Root: HKA; Subkey: "Software\Classes\ytdlp"; ValueType: string; ValueName: ""; ValueData: "URL:yt-dlp Downloader Protocol"; Flags: uninsdeletekey; Tasks: songpulse
Root: HKA; Subkey: "Software\Classes\ytdlp"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Tasks: songpulse
Root: HKA; Subkey: "Software\Classes\ytdlp\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\yt_dlp_app.exe"",0"; Tasks: songpulse
Root: HKA; Subkey: "Software\Classes\ytdlp\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\yt_dlp_app.exe"" ""%1"""; Tasks: songpulse

[Icons]
Name: "{autoprograms}\yt-dlp Downloader"; Filename: "{app}\yt_dlp_app.exe"
Name: "{autodesktop}\yt-dlp Downloader"; Filename: "{app}\yt_dlp_app.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\yt_dlp_app.exe"; Description: "Launch yt-dlp Downloader"; Flags: nowait postinstall skipifsilent

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var
  MissingMsg: String;
begin
  Result := True;
  if CurPageID = wpSelectComponents then
  begin
    MissingMsg := '';
    if not WizardIsComponentSelected('ffmpeg') then
      MissingMsg := MissingMsg + '• FFmpeg is deselected: Audio conversion (MP3/M4A/FLAC/WAV), cover art & metadata embedding, video format merging, time-clipping, and live preview will be disabled.' + #13#10 + #13#10;
    if not WizardIsComponentSelected('nodejs') then
      MissingMsg := MissingMsg + '• Node.js is deselected: Downloads have a higher chance of being blocked by YouTube signature/bot checks.' + #13#10 + #13#10;

    if MissingMsg <> '' then
    begin
      MissingMsg := 'Warning — Optional Dependencies Skipped:' + #13#10 + #13#10 +
                    MissingMsg +
                    '(You can still download or redownload FFmpeg and Node.js later anytime inside the app''s Settings tab.)' + #13#10 + #13#10 +
                    'Do you want to continue without these components?';
      if MsgBox(MissingMsg, mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;
