# SyncSentinel - Media Asset Watcher

![SyncSentinel Logo](syncsentinel_icon.png)

A comprehensive tool for monitoring and parsing FreeFileSync log files with automated CSV export and optional Google Sheets integration.

## Version

**Current Version: 0.9.0** (Pre-release)

This version represents a nearly complete implementation with all core features functional. Minor bugs may exist but do not prevent normal operation.

## Features

- **Real-time Monitoring**:## Google Sheets Setup

### Automated Setup (Recommended)

SyncSentinel now provides a **secure, automated setup process** that handles everything from within the application:

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Access Google Sheets**:
   - Click **Tools → Google Sheets** in the menu bar
   - Select the "Google Sheets" tab

3. **Follow the guided setup**:
   - The dialog provides step-by-step instructions
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Sheets API
   - Create OAuth 2.0 credentials (Desktop application)
   - Copy your Client ID, Client Secret, and Project ID

4. **Enter credentials in SyncSentinel**:
   - Paste your Client ID (masked for security)
   - Paste your Client Secret (masked for security)
   - Enter your Project ID
   - Click "Download Credentials"

5. **Complete authentication**:
   - Enter your Google Sheet ID or URL
   - Click "Authenticate" to complete OAuth flow

### Security Features

- **Encrypted Storage**: Credentials are automatically encrypted using AES-256 encryption
- **Secure Key Management**: Encryption keys are securely generated and stored
- **Masked Input**: Sensitive fields are masked to prevent shoulder surfing
- **No Manual File Handling**: Everything happens within the application
- **Token Security**: OAuth tokens are securely stored and automatically refreshed

### Manual Setup (Legacy)

If you prefer manual setup:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the `credentials.json` file
6. Place it in the project root directory

**Note**: Manual setup is less secure and more cumbersome than the automated process.tects new FreeFileSync log files
- **Dual Format Support**: Parses both `.log` and `.html` format log files
- **CSV Export**: Automatically exports parsed data to CSV with file type detection
- **Clipboard Integration**: Copy last parsed data to clipboard for easy sharing
- **System Tray**: Minimizes to system tray for unobtrusive operation
- **Google Sheets Integration**: Optional upload to Google Sheets with OAuth authentication
- **Modular Architecture**: Clean, maintainable code structure
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Comprehensive Testing**: Unit and integration tests included

## Project Structure

```
syncsentinel/
├── __init__.py              # Package initialization
├── main.py                  # Main GUI application and entry point
├── parser.py                # Log parsing and CSV writing functions
├── handler.py               # File system event handling
├── gui_utils.py             # GUI-specific helper functions
├── google_sheets.py         # Google Sheets API integration
├── tests.py                 # Unit and integration tests
├── build.py                 # PyInstaller build script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Requirements

- Python 3.6+
- watchdog
- pillow
- pystray
- tkinter (usually included with Python)
- google-api-python-client (for Google Sheets)
- google-auth-oauthlib (for Google Sheets)

## Installation

1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **For Google Sheets integration** (optional):
   - No manual file downloads required!
   - Setup is handled entirely within the application
   - Credentials are automatically encrypted and secured

## Data Storage

SyncSentinel stores user data in the appropriate system directories:

- **Windows**: `%APPDATA%\SyncSentinel\` (typically `C:\Users\<username>\AppData\Roaming\SyncSentinel\`)
- **macOS/Linux**: `~/.syncsentinel/`

This includes:
- Application settings (`config.json`)
- Encrypted Google Sheets credentials
- OAuth tokens

The uninstaller provides an option to remove this user data during uninstallation.

## Usage

### Basic Usage

1. **Run the application**:
   ```bash
   python main.py
   ```

2. **Configure paths**:
   - Set the folder to watch for FreeFileSync logs
   - Set the CSV output file path

3. **Start monitoring**:
   - Click "Start Watching" to begin real-time monitoring
   - Or "Process Existing Logs" to parse existing files

### Google Sheets Integration

1. **Setup Google Sheets**:
   - Click **Tools → Google Sheets** in the menu bar
   - Follow the guided setup process in the Google Sheets tab
   - Enter your Google Cloud credentials (automatically encrypted)
   - Authenticate with your Google account

2. **Configure Sheet**:
   - Enter your Google Sheet ID or full URL
   - Enable Google Sheets upload
   - Click "Authenticate" to complete setup

3. **Automatic Upload**:
   - Data will be automatically uploaded when new logs are processed
   - Existing data in the sheet will be replaced with new data

## File Formats Supported

### FreeFileSync .log Format
```
Test Sync 9/13/2025 [2:30:15 PM]
|    Items processed: 5 (1.2 MB)
|    Total time: 0:00:30
Info: Comparison finished: 5 items found – Time elapsed: 0:00:15
Synchronizing folder pair: Update >
Source: C:\Source
Dest: C:\Dest
Info: [2:30:20 PM] Creating file "C:\Dest\VideoFile\Project\test.mov"
```

### FreeFileSync .html Format
```html
<span style="font-weight:600; color:gray;">Test Sync</span>
9/13/2025
<span>2:30:15 PM</span>
<td valign="top">2:30:20 PM</td>
Creating file &quot;C:\Dest\VideoFile\Project\test.mov&quot;
```

## CSV Output Format

| Date       | Time       | Type  | Section | File Name  |
|------------|------------|-------|---------|------------|
| 9/13/2025 | 2:30:20 PM | Video | Project | test.mov   |
| 9/13/2025 | 2:30:25 PM | Image | Project | image.png  |

## File Type Detection

- **Video**: `.mov`
- **Image**: `.png`, `.jpeg`, `.jpg`, `.bmp`, `.tiff`, `.tif`, `.exr`, `.tga`, `.dpx`
- **Audio**: `.mp3`, `.wav`, `.aiff`
- **3D**: `.abc`, `.fbx`, `.obj`

## Testing

Run the comprehensive test suite:

```bash
python -m unittest tests.py
```

Tests include:
- Unit tests for parsing functions
- CSV writing functionality
- File system event handling
- GUI integration tests
- Google Sheets integration tests

## Building Standalone Executables

### Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

### Building

Run the build script:
```bash
python build.py
```

This will:
- Create a `SyncSentinel.spec` file
- Build a standalone executable in the `dist` folder
- Use the icon `syncsentinel_icon.png` if present

### Manual Build

You can also build manually:
```bash
pyinstaller --onefile --windowed --name=SyncSentinel --icon=syncsentinel_icon.png --hidden-import=pystray --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=tkinter --hidden-import=tkinter.filedialog --hidden-import=tkinter.scrolledtext --hidden-import=tkinter.messagebox --hidden-import=win32api --hidden-import=win32con --hidden-import=win32gui --hidden-import=win32service --hidden-import=pywintypes --add-data syncsentinel_icon.png;. main.py
```

### Building with Installer

To build both executable and installer:
```bash
python build.py --installer
```

#### Windows Installer (Inno Setup)

**Requirements:**
- Install Inno Setup from https://jrsoftware.org/isinfo.php
- Ensure `ISCC.exe` is in your PATH

The build script will:
- Generate `SyncSentinel.iss` Inno Setup script
- Compile it into an EXE installer in the `installers` folder
- Installer includes:
  - App installation to Program Files
  - Start menu shortcuts
  - Optional desktop shortcut
  - Uninstaller

#### macOS Installer (DMG)

**Requirements:**
- Install create-dmg:
  ```bash
  npm install -g create-dmg
  # or
  brew install create-dmg
  ```

The build script will:
- Create a `SyncSentinel.app` folder structure
- Generate `SyncSentinel.dmg` with drag-and-drop installation
- Includes app icon and Applications folder link

### Cross-Platform Builds

- **Windows executable/installer**: Build on a Windows machine
- **macOS executable/installer**: Build on a macOS machine

The build script handles platform-specific data inclusion automatically.

### Icon Handling

- Place `syncsentinel_icon.png` in the project root
- The build script will automatically convert PNG to ICO (Windows) or ICNS (macOS) if they don't exist
- PyInstaller can use PNG files, but for better results:
  - Windows: Convert to `.ico` format for installer
  - macOS: Convert to `.icns` format for DMG

## Google Sheets Setup

### 1. Google Cloud Console Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Google Sheets API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the `credentials.json` file

### 2. Sheet ID
- Your Google Sheet URL: `https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit`
- Use either the full URL or just the `SPREADSHEET_ID` part

### 3. Authentication
- First run will open a browser for OAuth authentication
- Token is saved locally for future use
- Re-authenticate if token expires

## Architecture

### Modular Design
- **main.py**: GUI and application lifecycle
- **parser.py**: Core parsing logic and data processing
- **handler.py**: File system monitoring and event handling
- **gui_utils.py**: GUI-specific utilities and callbacks
- **google_sheets.py**: Google API integration

### Key Classes
- `MediaAssetWatcherGUI`: Main GUI application
- `LogFileHandler`: File system event handler
- `GoogleSheetsManager`: Google Sheets API manager

## Error Handling

- Comprehensive error logging in the activity log
- Graceful fallback for clipboard operations
- Google Sheets authentication error handling
- File parsing error recovery

## Security

- **AES-256 Encryption**: Google Sheets credentials are automatically encrypted using industry-standard AES-256 encryption
- **Secure Key Management**: Encryption keys are generated using PBKDF2 with salt and high iteration count
- **OAuth 2.0**: Secure authentication with Google using OAuth 2.0 protocol
- **Token Security**: OAuth tokens are securely stored and automatically refreshed
- **No Plaintext Storage**: Sensitive credentials are never stored in plaintext
- **Masked Input Fields**: Client ID and Client Secret fields are masked for security
- **Automated Setup**: No manual file handling reduces risk of credential exposure

## Contributing

1. Follow the modular structure
2. Add tests for new functionality
3. Update documentation
4. Test on multiple platforms

## License

This project is open source. Please refer to individual file headers for licensing information.
