#!/usr/bin/env python3
"""
Build script for SyncSentinel using PyInstaller.
This script creates standalone executables and optional installers for Windows and macOS.
"""

import os
import platform
import shutil
import subprocess
import sys
import argparse

# Import version from main module
try:
    from syncsentinel.main import VERSION
except ImportError:
    VERSION = "0.9.0"  # Fallback version

def convert_icon_formats():
    """Convert syncsentinel_icon.png to platform-specific formats if they don't exist."""
    
    png_path = 'assets/syncsentinel_icon.png'
    if not os.path.exists(png_path):
        print("assets/syncsentinel_icon.png not found, skipping icon conversion")
        return
    
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed. Install with: pip install pillow")
        print("Skipping icon conversion")
        return
    
    current_platform = platform.system()
    
    if current_platform == 'Windows':
        ico_path = 'assets/syncsentinel_icon.ico'
        if not os.path.exists(ico_path):
            try:
                img = Image.open(png_path)
                img.save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (256,256)])
                print(f"Converted {png_path} to {ico_path}")
            except Exception as e:
                print(f"Error converting to ICO: {e}")
    elif current_platform == 'Darwin':  # macOS
        icns_path = 'assets/syncsentinel_icon.icns'
        if not os.path.exists(icns_path):
            try:
                img = Image.open(png_path)
                img.save(icns_path, format='ICNS')
                print(f"Converted {png_path} to {icns_path}")
            except Exception as e:
                print(f"Error converting to ICNS: {e}")

def build_executable():
    """Build the executable using PyInstaller."""
    
    # Determine platform-specific settings
    current_platform = platform.system()
    
        # Base PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', f'SyncSentinel-{VERSION}',
        '--icon=assets/syncsentinel_icon.ico',
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.scrolledtext',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--hidden-import=win32gui',
        '--hidden-import=win32service',
        '--hidden-import=pywintypes',
        '--hidden-import=googleapiclient.discovery',
        '--hidden-import=google_auth_oauthlib.flow',
        '--hidden-import=google.auth.transport.requests',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=cryptography.hazmat.primitives',
        '--hidden-import=cryptography.hazmat.primitives.kdf.pbkdf2',
        '--hidden-import=watchdog.events',
        '--hidden-import=watchdog.observers',
        '--hidden-import=watchdog.observers.fsevents',
        '--hidden-import=watchdog.observers.read_directory_changes',
        '--hidden-import=watchdog.observers.inotify_buffer',
        '--paths=.',
    ]
    
    # Add platform-specific options
    if current_platform == 'Windows':
        # Windows-specific options
        cmd.extend([
            '--add-data', 'assets/syncsentinel_icon.ico;.',
            '--add-data', 'assets/syncsentinel_icon.png;.',
        ])
    elif current_platform == 'Darwin':  # macOS
        # macOS-specific options
        cmd.extend([
            '--add-data', 'assets/syncsentinel_icon.ico:.',
            '--add-data', 'assets/syncsentinel_icon.png:.',
        ])
    else:
        print(f"Unsupported platform: {current_platform}")
        return False
    
    # Add the main script
    cmd.append('syncsentinel/main.py')
    
    print("Building SyncSentinel executable...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        print("Executable created in 'dist' folder")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def create_spec_file():
    """Create a .spec file for PyInstaller."""
    
    spec_filename = f'SyncSentinel-{VERSION}.spec'
    
    # Check if spec file exists and is up to date
    if os.path.exists(spec_filename):
        with open(spec_filename, 'r') as f:
            content = f.read()
            if f"name='SyncSentinel-{VERSION}'" in content:
                print(f"Spec file {spec_filename} already exists and is up to date.")
                return
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['syncsentinel/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/syncsentinel_icon.ico', '.'), ('assets/syncsentinel_icon.png', '.')],
    hiddenimports=[
        'watchdog.events',
        'watchdog.observers',
        'watchdog.observers.fsevents',  # macOS
        'watchdog.observers.read_directory_changes',  # Windows
        'watchdog.observers.inotify_buffer',  # Linux
        'pystray',
        'PIL',
        'PIL.Image',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.ttk',
        'win32api',
        'win32con',
        'win32gui',
        'win32service',
        'pywintypes',
        'googleapiclient.discovery',
        'google_auth_oauthlib.flow',
        'google.auth.transport.requests',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'parser',
        'handler',
        'gui_utils',
        'google_sheets',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SyncSentinel-{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/syncsentinel_icon.ico',
)
'''
    
    with open(spec_filename, 'w') as f:
        f.write(spec_content)
    
    print(f"Created {spec_filename}")

def create_inno_setup_iss():
    """Create Inno Setup Script (ISS) file for Windows installer."""
    
    # Convert PNG to ICO if needed
    try:
        from PIL import Image
        ico_path = 'assets/syncsentinel_icon.ico'
        png_path = 'assets/syncsentinel_icon.png'
        
        if not os.path.exists(ico_path) and os.path.exists(png_path):
            img = Image.open(png_path)
            img.save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (256,256)])
            print("Converted assets/syncsentinel_icon.png to assets/syncsentinel_icon.ico")
        elif not os.path.exists(ico_path):
            print("Warning: Neither assets/syncsentinel_icon.ico nor assets/syncsentinel_icon.png found")
    except ImportError:
        print("Pillow not installed. Install with: pip install pillow")
        print("Using PNG icon for installer (ICO recommended for better compatibility)")
    except Exception as e:
        print(f"Error converting icon: {e}")
        print("Using PNG icon for installer")
    
    # Clean up old installer files
    os.makedirs('installers', exist_ok=True)
    for f in os.listdir('installers'):
        if f.startswith('SyncSentinel-') and (f.endswith('.exe') or f.endswith('.iss')):
            os.remove(os.path.join('installers', f))
            print(f"Cleaned up old file: {f}")
    
    iss_content = f'''[Setup]
AppId={{{{B5A7F0E0-1234-5678-9ABC-DEF012345678}}}}
AppName=SyncSentinel
AppVersion={VERSION}
AppPublisher=SyncSentinel Development
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={{pf}}\\SyncSentinel
DefaultGroupName=SyncSentinel
OutputDir=installers
OutputBaseFilename=SyncSentinel-{VERSION}-Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets/syncsentinel_icon.ico
UninstallDisplayIcon={{app}}\\assets\\syncsentinel_icon.ico
UninstallDisplayName=SyncSentinel v{VERSION}
VersionInfoVersion={VERSION}
VersionInfoProductVersion={VERSION}
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create Start Menu icon"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "dist\\SyncSentinel-{VERSION}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "assets/syncsentinel_icon.ico"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "assets/syncsentinel_icon.png"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\SyncSentinel"; Filename: "{{app}}\\SyncSentinel-{VERSION}.exe"; IconFilename: "{{app}}\\assets\\syncsentinel_icon.ico"; Tasks: startmenuicon
Name: "{{commondesktop}}\\SyncSentinel"; Filename: "{{app}}\\SyncSentinel-{VERSION}.exe"; IconFilename: "{{app}}\\assets\\syncsentinel_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\SyncSentinel-{VERSION}.exe"; Description: "{{cm:LaunchProgram,SyncSentinel}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Prompt to remove user data
    if MsgBox('Do you want to remove user data and settings (including credentials and config from AppData\\Roaming\\SyncSentinel)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UserDataPath := ExpandConstant('{{userappdata}}\\SyncSentinel');
      if DirExists(UserDataPath) then
      begin
        DelTree(UserDataPath, True, True, True);
      end;
    end;
  end;
end;
'''
    
    print("Generated .iss content preview:")
    print(iss_content[:500] + "...")  # Print first 500 chars for debugging
    
    with open(f'SyncSentinel-{VERSION}.iss', 'w') as f:
        f.write(iss_content)
    
    print(f"Created SyncSentinel-{VERSION}.iss file")

def build_windows_installer():
    """Build Windows installer using Inno Setup."""
    
    create_inno_setup_iss()
    
    # Debug: Check iscc path
    print(f"iscc path: {shutil.which('iscc')}")
    
    # Determine iscc command
    if shutil.which('iscc') is None:
        cmd = [r'C:\Program Files (x86)\Inno Setup 6\iscc.exe', f'SyncSentinel-{VERSION}.iss']
    else:
        cmd = ['iscc', f'SyncSentinel-{VERSION}.iss']
    
    print("Building Windows installer...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Windows installer created successfully!")
        print("Installer located in 'installers' folder")
        
        # Verify the output exe name
        expected_name = f"SyncSentinel-{VERSION}-Installer.exe"
        installer_path = os.path.join('installers', expected_name)
        if os.path.exists(installer_path):
            print(f"Verified installer created: {expected_name}")
        else:
            print(f"Warning: Expected installer {expected_name} not found")
            if os.path.exists('installers'):
                files = os.listdir('installers')
                print(f"Files in installers: {files}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Installer build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def build_mac_installer():
    """Build macOS DMG installer using create-dmg."""
    
    # Check if create-dmg is installed
    try:
        result = subprocess.run(['create-dmg', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, OSError):
        print("create-dmg not found. Install with:")
        print("npm install -g create-dmg")
        print("or")
        print("brew install create-dmg")
        return False
    
    # Create a temporary app folder
    app_folder = 'dist/SyncSentinel.app'
    os.makedirs(app_folder, exist_ok=True)
    
    # Copy executable and icon
    import shutil
    shutil.copy('dist/SyncSentinel', f'{app_folder}/SyncSentinel')
    if os.path.exists('assets/syncsentinel_icon.png'):
        shutil.copy('assets/syncsentinel_icon.png', f'{app_folder}/')
    
    # Make executable
    os.chmod(f'{app_folder}/SyncSentinel', 0o755)
    
    # Create DMG
    cmd = [
        'create-dmg',
        '--volname', 'SyncSentinel',
        '--volicon', 'assets/syncsentinel_icon.png' if os.path.exists('assets/syncsentinel_icon.png') else '',
        '--window-pos', '200', '120',
        '--window-size', '800', '400',
        '--icon-size', '100',
        '--icon', 'SyncSentinel.app', '200', '190',
        '--hide-extension', 'SyncSentinel.app',
        '--app-drop-link', '600', '185',
        'SyncSentinel.dmg',
        app_folder
    ]
    
    # Remove empty volicon if no icon
    if not os.path.exists('assets/syncsentinel_icon.png'):
        cmd.remove('--volicon')
        cmd.remove('assets/syncsentinel_icon.png')
    
    print("Building macOS DMG installer...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("macOS DMG installer created successfully!")
        print("DMG file: SyncSentinel.dmg")
        return True
    except subprocess.CalledProcessError as e:
        print(f"DMG build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def build_installer():
    """Build platform-specific installer."""
    
    current_platform = platform.system()
    
    if current_platform == 'Windows':
        return build_windows_installer()
    elif current_platform == 'Darwin':
        return build_mac_installer()
    else:
        print(f"Installer not supported for platform: {current_platform}")
        return False

def main():
    """Main build function."""
    
    parser = argparse.ArgumentParser(description='Build SyncSentinel executable and optional installer')
    parser.add_argument('--installer', action='store_true', help='Build installer after executable')
    args = parser.parse_args()
    
    print("SyncSentinel Build Script")
    print("=" * 30)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Check if icon exists
    if not os.path.exists('assets/syncsentinel_icon.ico'):
        print("Warning: assets/syncsentinel_icon.ico not found in project root")
        print("The build will continue but without an icon")
    
    # Convert icon formats if needed
    convert_icon_formats()
    
    # Create .spec file
    create_spec_file()
    
    # Build executable
    success = build_executable()
    
    if success:
        print("\nExecutable build completed successfully!")
        if args.installer:
            print("\nBuilding installer...")
            installer_success = build_installer()
            if installer_success:
                print("Installer build completed successfully!")
            else:
                print("Installer build failed.")
        else:
            print("To build installer, run with --installer flag")
        print(f"\nTo build for the other platform, run this script on that platform.")
        print("For Windows: Run on Windows machine")
        print("For macOS: Run on macOS machine")
    else:
        print("\nBuild failed. Check the error messages above.")

if __name__ == '__main__':
    main()
