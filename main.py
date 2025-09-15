"""
SyncSentinel Main Module
Entry point and main GUI application.
"""

import os
import sys
import platform
import subprocess
import threading
import json
from watchdog.observers import Observer

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import tkinter.ttk as ttk

from parser import parse_sync_log, append_to_csv
from handler import LogFileHandler
from gui_utils import (
    store_last_parsed, log_message, copy_last_log,
    setup_tray_icon, show_window, quit_app, minimize_to_tray
)
from google_sheets import GoogleSheetsManager

# Version information
VERSION = "0.9.0"


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MediaAssetWatcherGUI:
    """
    Main GUI application for SyncSentinel.
    """

    def __init__(self, root):
        print("SyncSentinel starting...")
        self.root = root
        self.root.title("SyncSentinel")
        self.root.geometry("900x575")
        try:
            self.root.iconbitmap(resource_path('syncsentinel_icon.ico'))
        except Exception:
            pass  # Icon not found, continue without it

        # Initialize variables
        self.watching = False
        self.observer = None
        self.watch_path = ""
        self.csv_file = ""
        self.last_parsed_data = None
        self.last_parsed_date = None
        self.google_sheets_enabled = False
        self.google_sheet_id = ""
        self.google_sheet_name = None
        self.google_credentials = None
        self.google_sheet_url = ""
        
        # Use proper Windows AppData location for user data
        if platform.system() == 'Windows':
            self.config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SyncSentinel')
        else:
            # For other platforms, use home directory
            self.config_dir = os.path.join(os.path.expanduser('~'), '.syncsentinel')
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, 'config.json')
        
        # Settings
        self.dark_mode = False
        self.log_breaks = True
        self.prepend_mode = True
        
        self.sheets_manager = GoogleSheetsManager()

        # Load configuration
        self.load_config()

        # Setup UI
        self.setup_ui()

        # Update UI with loaded config
        self.update_ui_from_config()

        # Setup tray icon
        self.setup_tray_icon()

        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Setup the user interface."""
        # Create menu bar
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Exit", command=self.quit_app)

        # Tools menu
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Google Sheets", command=self.show_google_sheets_dialog)
        self.tools_menu.add_command(label="Settings", command=self.show_settings_dialog)

        # Help menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=self.show_about)

        # Folder selection
        self.folder_frame = tk.Frame(self.root)
        self.folder_frame.pack(pady=10)

        self.folder_label = tk.Label(self.folder_frame, text="Watch Folder:")
        self.folder_label.pack(side=tk.LEFT)

        self.folder_entry = tk.Entry(self.folder_frame, width=60)
        self.folder_entry.pack(side=tk.LEFT, padx=5)

        # Set default path based on OS
        if platform.system() == 'Windows':
            default_logs_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'FreeFileSync', 'Logs')
        elif platform.system() == 'Darwin':  # macOS
            default_logs_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'FreeFileSync', 'Logs')
        else:
            default_logs_path = ''  # Default empty for other OS

        self.folder_entry.insert(0, default_logs_path)

        self.set_folder_button = tk.Button(self.folder_frame, text="Set Folder", command=self.set_folder)
        self.set_folder_button.pack(side=tk.LEFT)

        self.open_folder_button = tk.Button(self.folder_frame, text="Open Folder", command=self.open_current_folder, state=tk.DISABLED)
        self.open_folder_button.pack(side=tk.LEFT)

        # CSV file selection
        self.csv_frame = tk.Frame(self.root)
        self.csv_frame.pack(pady=10)

        self.csv_label = tk.Label(self.csv_frame, text="CSV Output File:")
        self.csv_label.pack(side=tk.LEFT)

        self.csv_entry = tk.Entry(self.csv_frame, width=60)
        self.csv_entry.pack(side=tk.LEFT, padx=5)

        # Set default CSV path inside the default watch folder
        default_csv_path = os.path.join(default_logs_path, 'media_assets.csv') if default_logs_path else 'media_assets.csv'
        self.csv_entry.insert(0, default_csv_path)

        self.set_csv_button = tk.Button(self.csv_frame, text="Set File", command=self.set_csv)
        self.set_csv_button.pack(side=tk.LEFT)

        self.open_csv_button = tk.Button(self.csv_frame, text="Open File", command=self.open_current_csv, state=tk.DISABLED)
        self.open_csv_button.pack(side=tk.LEFT)

        # Google Sheets integration
        self.sheets_frame = tk.Frame(self.root)
        self.sheets_frame.pack(pady=10)

        self.sheets_var = tk.BooleanVar()
        self.sheets_checkbox = tk.Checkbutton(self.sheets_frame, text="Upload to Google Sheets",
                                            variable=self.sheets_var, command=self.toggle_google_sheets)
        self.sheets_checkbox.pack(side=tk.LEFT)

        # Initialize Google Sheets state
        self.update_google_sheets_ui()

        # Control buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)

        self.start_button = tk.Button(self.button_frame, text="Start Watching", command=self.start_watching, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.process_button = tk.Button(self.button_frame, text="Process Existing Logs", command=self.process_existing_logs, state=tk.DISABLED)
        self.process_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop Watching", command=self.stop_watching, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.copy_button = tk.Button(self.button_frame, text="Copy Last Log", command=self.copy_last_log, state=tk.DISABLED)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        # Log area
        self.log_label = tk.Label(self.root, text="Activity Log:")
        self.log_label.pack(anchor=tk.W, padx=10)

        # Create a frame for the log text with scrollbars
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Create text widget with no wrap
        self.log_text = scrolledtext.ScrolledText(self.log_frame, width=70, height=15, wrap=tk.NONE)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Bind entries change
        self.folder_entry.bind('<KeyRelease>', self.check_inputs)
        self.csv_entry.bind('<KeyRelease>', self.check_inputs)
        self.csv_entry.bind('<FocusOut>', self.add_csv_extension)

        # Check inputs initially to enable buttons if defaults are valid
        self.check_inputs()
        
        # Apply theme
        if self.dark_mode:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()

    def setup_tray_icon(self):
        """Setup system tray icon."""
        setup_tray_icon(self)

    def show_window(self, icon=None, item=None):
        """Show the main window from tray."""
        show_window(self, icon, item)

    def quit_app(self, icon=None, item=None):
        """Quit the application from tray."""
        self.save_config()
        quit_app(self, icon, item)

    def on_closing(self):
        """Handle window close event."""
        self.save_config()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.minimize_to_tray()
        else:
            self.quit_app()

    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.watch_path = config.get('watch_path', self.watch_path)
                self.csv_file = config.get('csv_file', self.csv_file)
                self.google_sheets_enabled = config.get('google_sheets_enabled', False)
                self.google_sheet_url = config.get('google_sheet_url', '')
                self.dark_mode = config.get('dark_mode', False)
                self.log_breaks = config.get('log_breaks', True)
                self.prepend_mode = config.get('prepend_mode', True)
                if self.google_sheet_url:
                    sheet_info = self.sheets_manager.extract_sheet_info(self.google_sheet_url)
                    self.google_sheet_id = sheet_info['spreadsheet_id']
                    self.google_sheet_name = sheet_info['sheet_name']
            except Exception as e:
                self.log_message(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file."""
        try:
            config = {
                'watch_path': self.watch_path,
                'csv_file': self.csv_file,
                'google_sheets_enabled': self.google_sheets_enabled,
                'google_sheet_url': self.google_sheet_url,
                'dark_mode': self.dark_mode,
                'log_breaks': self.log_breaks,
                'prepend_mode': self.prepend_mode
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            self.log_message(f"Error saving config: {e}")

    def update_ui_from_config(self):
        """Update UI elements with loaded configuration."""
        if self.watch_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, self.watch_path)
        if self.csv_file:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, self.csv_file)
        self.sheets_var.set(self.google_sheets_enabled)
        self.update_google_sheets_ui()

    def minimize_to_tray(self):
        """Minimize window to system tray instead of closing."""
        minimize_to_tray(self)

    def set_folder(self):
        current_path = self.folder_entry.get()
        initial_dir = current_path if os.path.isdir(current_path) else None
        folder = filedialog.askdirectory(initialdir=initial_dir)
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.check_inputs()
            self.save_config()

    def open_current_folder(self):
        if self.watch_path:
            self.open_folder(self.watch_path)

    def set_csv(self):
        current_path = self.csv_entry.get()
        initial_dir = os.path.dirname(current_path) if current_path else None
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=initial_dir
        )
        if file_path:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, file_path)
            self.check_inputs()
            self.save_config()

    def open_current_csv(self):
        if self.csv_file and os.path.isfile(self.csv_file):
            try:
                if platform.system() == 'Windows':
                    os.startfile(self.csv_file)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', self.csv_file])
                else:  # Linux and others
                    subprocess.run(['xdg-open', self.csv_file])
            except Exception as e:
                self.log_message(f"Could not open CSV file: {e}")
        else:
            self.log_message("CSV file does not exist yet.")

    def open_folder(self, path):
        """Cross-platform function to open a folder in the file explorer."""
        try:
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', path])
            else:  # Linux and others
                subprocess.run(['xdg-open', path])
        except Exception as e:
            self.log_message(f"Could not open folder: {e}")

    def add_csv_extension(self, event=None):
        csv_path = self.csv_entry.get()
        if csv_path.strip() and not csv_path.lower().endswith('.csv'):
            self.csv_entry.insert(tk.END, '.csv')
            self.check_inputs()

    def update_google_sheets_ui(self):
        """Update the main window Google Sheets UI based on current state."""
        # Update checkbox
        self.sheets_var.set(self.google_sheets_enabled)

        # Update control states
        self.toggle_google_sheets()

    def toggle_google_sheets(self):
        """Toggle Google Sheets integration."""
        self.google_sheets_enabled = self.sheets_var.get()
        if self.google_sheets_enabled and not self.google_sheet_id:
            messagebox.showinfo("Google Sheets Setup Required", 
                                "Google Sheets integration is enabled, but no sheet is configured.\n\n"
                                "Please go to Tools → Google Sheets to configure your Google Sheet URL/ID.")
        self.save_config()

    def authenticate_google(self):
        """Authenticate with Google Sheets API."""
        try:
            self.log_message("Authenticating with Google Sheets...")
            # Only update dialog status if dialog is open
            if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                self.dialog_status_label.config(text="Authenticating...", fg="blue")
                self.root.update()

            success, message = self.sheets_manager.authenticate()
            if success:
                self.log_message("Google Sheets authentication completed")
                # Only update dialog status if dialog is open
                if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                    self.dialog_status_label.config(text="Authentication successful", fg="green")
                    self.update_setup_status()

                # Update main window UI
                self.update_google_sheets_ui()
            else:
                self.log_message(f"Google Sheets authentication failed: {message}")
                # Only update dialog status if dialog is open
                if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                    self.dialog_status_label.config(text=f"Authentication failed: {message}", fg="red")
        except Exception as e:
            self.log_message(f"Google Sheets authentication failed: {e}")
            # Only update dialog status if dialog is open
            if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                self.dialog_status_label.config(text=f"Error: {str(e)}", fg="red")

    def upload_to_google_sheets(self, parsed_data):
        """Upload parsed data to Google Sheets."""
        try:
            if not self.google_sheet_id:
                self.log_message("No Google Sheet ID configured")
                return

            self.log_message("Uploading data to Google Sheets...")
            success, message = self.sheets_manager.upload_data(
                self.google_sheet_id, 
                parsed_data, 
                self.google_sheet_name,
                prepend=self.prepend_mode,
                add_breaks=self.log_breaks
            )
            if success:
                self.log_message(message)
            else:
                self.log_message(f"Failed to upload data to Google Sheets: {message}")
        except Exception as e:
            self.log_message(f"Error uploading to Google Sheets: {e}")

    def store_last_parsed(self, parsed_data):
        """Store parsed data for clipboard access."""
        store_last_parsed(self, parsed_data)

    def log_message(self, message):
        """Log a message to the GUI."""
        log_message(self, message)

    def check_inputs(self, event=None):
        folder_path = self.folder_entry.get()
        csv_path = self.csv_entry.get()

        folder_valid = os.path.isdir(folder_path)
        csv_valid = bool(csv_path.strip())

        if folder_valid and csv_valid:
            self.watch_path = folder_path
            self.csv_file = csv_path
            self.start_button.config(state=tk.NORMAL)
            self.process_button.config(state=tk.NORMAL)
            self.open_folder_button.config(state=tk.NORMAL)
            self.open_csv_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)
            self.process_button.config(state=tk.DISABLED)
            self.open_folder_button.config(state=tk.DISABLED)
            self.open_csv_button.config(state=tk.DISABLED)

    def copy_last_log(self):
        """Copy the last parsed log data to clipboard."""
        copy_last_log(self)

    def start_watching(self):
        if not self.watch_path:
            messagebox.showerror("Error", "Please select a valid folder to watch.")
            return

        self.watching = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.process_button.config(state=tk.DISABLED)
        self.set_folder_button.config(state=tk.DISABLED)
        self.set_csv_button.config(state=tk.DISABLED)
        self.open_folder_button.config(state=tk.NORMAL)
        self.open_csv_button.config(state=tk.NORMAL)
        self.folder_entry.config(state=tk.DISABLED)
        self.csv_entry.config(state=tk.DISABLED)

        # Start watching
        self.log_message(f"Starting to watch {self.watch_path} for new log files...")
        sheets_callback = self.upload_to_google_sheets if self.google_sheets_enabled and self.google_sheet_id else None
        event_handler = LogFileHandler(self.csv_file, self.log_message, self.store_last_parsed, sheets_callback, prepend=self.prepend_mode, add_breaks=self.log_breaks)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_path, recursive=False)
        self.observer.start()

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.watching = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.process_button.config(state=tk.NORMAL)
        self.set_folder_button.config(state=tk.NORMAL)
        self.set_csv_button.config(state=tk.NORMAL)
        self.open_folder_button.config(state=tk.NORMAL)
        self.open_csv_button.config(state=tk.NORMAL)
        self.folder_entry.config(state=tk.NORMAL)
        self.csv_entry.config(state=tk.NORMAL)
        self.log_message("Stopped watching.")

    def process_existing_logs(self):
        if not self.watch_path:
            messagebox.showerror("Error", "Please select a valid folder to watch.")
            return

        # Get list of log files and sort by creation date (newest first)
        log_files = [f for f in os.listdir(self.watch_path) if f.endswith(('.log', '.html'))]
        log_files.sort(key=lambda x: os.path.getctime(os.path.join(self.watch_path, x)), reverse=True)

        if not log_files:
            messagebox.showinfo("Info", "No log files found in the watch folder.")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Log Files to Process")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # Listbox
        listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE, height=15)
        listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        for f in log_files:
            listbox.insert(tk.END, f)

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=5)

        def on_ok():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("Warning", "No files selected.")
                return

            selected_files = [log_files[i] for i in selected_indices]
            dialog.destroy()

            # Process selected files
            self.log_message(f"Processing {len(selected_files)} selected log files...")
            processed_count = 0
            for filename in selected_files:
                log_path = os.path.join(self.watch_path, filename)
                self.log_message(f"Processing: {filename}")
                try:
                    parsed_data = parse_sync_log(log_path)
                    append_to_csv(parsed_data, self.csv_file, prepend=self.prepend_mode, add_breaks=self.log_breaks)
                    self.store_last_parsed(parsed_data)

                    # Upload to Google Sheets if enabled
                    if self.google_sheets_enabled and self.google_sheet_id:
                        self.upload_to_google_sheets(parsed_data)

                    processed_count += 1
                except Exception as e:
                    self.log_message(f"Error processing {filename}: {e}")
            self.log_message(f"Successfully processed {processed_count} log files.")

        def on_cancel():
            dialog.destroy()

        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def show_google_sheets_dialog(self):
        """Show the Google Sheets configuration dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Google Sheets")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        try:
            dialog.iconbitmap(resource_path('syncsentinel_icon.ico'))
        except Exception:
            pass  # Icon not found, continue without it

        # Create notebook for tabs
        notebook = tk.ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Google Sheets tab
        sheets_frame = tk.Frame(notebook)
        notebook.add(sheets_frame, text="Google Sheets")

        # Setup instructions
        instructions_frame = tk.LabelFrame(sheets_frame, text="Setup Instructions", padx=10, pady=10)
        instructions_frame.pack(fill=tk.X, pady=(0, 10))

        instructions_text = tk.Text(instructions_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        instructions_text.pack(fill=tk.X)

        setup_info = self.sheets_manager.get_setup_instructions()
        instructions_text.config(state=tk.NORMAL)
        instructions_text.delete(1.0, tk.END)
        instructions_text.insert(tk.END, "\n".join(setup_info['steps']))
        instructions_text.config(state=tk.DISABLED)

        # Credentials input
        creds_frame = tk.LabelFrame(sheets_frame, text="Google Cloud Credentials", padx=10, pady=10)
        creds_frame.pack(fill=tk.X, pady=(0, 10))

        # Client ID
        client_id_frame = tk.Frame(creds_frame)
        client_id_frame.pack(fill=tk.X, pady=2)
        tk.Label(client_id_frame, text="Client ID:").pack(side=tk.LEFT)
        self.client_id_entry = tk.Entry(client_id_frame, width=50, show="*")
        self.client_id_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Client Secret
        client_secret_frame = tk.Frame(creds_frame)
        client_secret_frame.pack(fill=tk.X, pady=2)
        tk.Label(client_secret_frame, text="Client Secret:").pack(side=tk.LEFT)
        self.client_secret_entry = tk.Entry(client_secret_frame, width=50, show="*")
        self.client_secret_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Project ID
        project_id_frame = tk.Frame(creds_frame)
        project_id_frame.pack(fill=tk.X, pady=2)
        tk.Label(project_id_frame, text="Project ID:").pack(side=tk.LEFT)
        self.project_id_entry = tk.Entry(project_id_frame, width=50)
        self.project_id_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Buttons frame
        creds_buttons_frame = tk.Frame(creds_frame)
        creds_buttons_frame.pack(pady=5)

        # Download button
        self.download_button = tk.Button(creds_buttons_frame, text="Download Credentials",
                                       command=self.download_credentials)
        self.download_button.pack(side=tk.LEFT, padx=(0, 5))

        # Remove credentials button
        self.remove_button = tk.Button(creds_buttons_frame, text="Remove Credentials",
                                     command=self.remove_credentials)
        self.remove_button.pack(side=tk.LEFT)

        # Authenticate button
        self.dialog_auth_button = tk.Button(creds_frame, text="Authenticate Credentials", command=self.authenticate_google)
        self.dialog_auth_button.pack(pady=5)

        # Status label
        self.dialog_status_label = tk.Label(creds_frame, text="", fg="blue")
        self.dialog_status_label.pack(anchor=tk.W, pady=5)

        # Configuration section
        config_frame = tk.LabelFrame(sheets_frame, text="Configuration", padx=10, pady=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # Enable checkbox
        self.dialog_sheets_var = tk.BooleanVar(value=self.google_sheets_enabled)
        enable_checkbox = tk.Checkbutton(config_frame, text="Enable Google Sheets upload",
                                       variable=self.dialog_sheets_var, command=self.toggle_dialog_sheets)
        enable_checkbox.pack(anchor=tk.W)

        # Sheet ID entry
        id_frame = tk.Frame(config_frame)
        id_frame.pack(fill=tk.X, pady=5)

        id_label = tk.Label(id_frame, text="Sheet ID/URL:")
        id_label.pack(side=tk.LEFT)

        self.dialog_sheets_entry = tk.Entry(id_frame, width=40)
        self.dialog_sheets_entry.pack(side=tk.LEFT, padx=5)
        # Initialize with current sheet URL if available
        if self.google_sheet_url:
            self.dialog_sheets_entry.insert(0, self.google_sheet_url)
            # If sheet is already configured, disable the entry and button
            self.dialog_sheets_entry.config(state=tk.DISABLED)

        # Set Sheet button
        self.set_sheet_button = tk.Button(id_frame, text="Set Sheet", command=self.set_sheet)
        self.set_sheet_button.pack(side=tk.LEFT, padx=(5, 0))
        # If sheet is already configured, disable the button
        if self.google_sheet_url:
            self.set_sheet_button.config(state=tk.DISABLED)

        # Clear URL button
        self.clear_url_button = tk.Button(id_frame, text="Clear URL", command=self.clear_sheet_url)
        self.clear_url_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Note about double-clicking
        tk.Label(id_frame, text="(double-click to clear)").pack(side=tk.LEFT, padx=(5, 0))

        # Status label
        self.dialog_status_label = tk.Label(creds_frame, text="", fg="blue")
        self.dialog_status_label.pack(anchor=tk.W, pady=5)

        # Update dialog state
        self.toggle_dialog_sheets()

        # Update credentials UI
        self.update_credentials_ui()

        # Check setup status
        self.update_setup_status()

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def on_ok():
            # Sync values from dialog to main window
            self.google_sheets_enabled = self.dialog_sheets_var.get()
            dialog_sheet_id = self.dialog_sheets_entry.get().strip()

            if dialog_sheet_id:
                self.google_sheet_url = dialog_sheet_id
                sheet_info = self.sheets_manager.extract_sheet_info(dialog_sheet_id)
                if sheet_info['spreadsheet_id']:
                    self.google_sheet_id = sheet_info['spreadsheet_id']
                    self.google_sheet_name = sheet_info['sheet_name']
                else:
                    self.log_message("Invalid Google Sheets URL or ID")
            else:
                self.google_sheet_url = ""
                self.google_sheet_id = ""
                self.google_sheet_name = None

            # Update main window checkbox
            self.sheets_var.set(self.google_sheets_enabled)
            self.update_google_sheets_ui()
            self.save_config()

            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def toggle_dialog_sheets(self):
        """Toggle Google Sheets controls in the Google Sheets dialog."""
        enabled = self.dialog_sheets_var.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.dialog_sheets_entry.config(state=state)
        self.set_sheet_button.config(state=state)

    def download_credentials(self):
        """Download and setup Google Sheets credentials."""
        try:
            client_id = self.client_id_entry.get().strip()
            client_secret = self.client_secret_entry.get().strip()
            project_id = self.project_id_entry.get().strip()

            if not all([client_id, client_secret, project_id]):
                self.dialog_status_label.config(text="Please fill in all credential fields", fg="red")
                return

            self.dialog_status_label.config(text="Downloading credentials...", fg="blue")
            self.root.update()

            if self.sheets_manager.download_credentials(client_id, client_secret, project_id):
                self.dialog_status_label.config(text="Credentials downloaded successfully!", fg="green")
                self.log_message("Google Sheets credentials downloaded and encrypted")

                # Show popup confirmation
                messagebox.showinfo("Credentials Downloaded",
                                  "Google Sheets credentials have been successfully downloaded and encrypted!\n\n"
                                  "You can now proceed to the Configuration section to enable Google Sheets upload and authenticate.")

                # Clear the credential fields for security
                self.client_id_entry.delete(0, tk.END)
                self.client_secret_entry.delete(0, tk.END)
                self.project_id_entry.delete(0, tk.END)

                # Update UI to show credentials are active
                self.update_credentials_ui()

                # Update setup status
                self.update_setup_status()
            else:
                self.dialog_status_label.config(text="Failed to download credentials", fg="red")

        except Exception as e:
            self.dialog_status_label.config(text=f"Error: {str(e)}", fg="red")
            self.log_message(f"Error downloading credentials: {e}")

    def remove_credentials(self):
        """Remove Google Sheets credentials."""
        try:
            # Confirm removal
            if not messagebox.askyesno("Remove Credentials",
                                     "Are you sure you want to remove the Google Sheets credentials?\n\n"
                                     "This will delete the encrypted credentials and you will need to re-enter them."):
                return

            # Remove credential files
            import os
            files_to_remove = [
                self.sheets_manager.ENCRYPTED_CREDENTIALS_FILE,
                self.sheets_manager.CREDENTIALS_FILE,
                self.sheets_manager.TOKEN_FILE,
                self.sheets_manager.KEY_FILE
            ]

            removed_count = 0
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1

            if removed_count > 0:
                self.log_message(f"Removed {removed_count} credential files")
                messagebox.showinfo("Credentials Removed",
                                  "Google Sheets credentials have been successfully removed.\n\n"
                                  "You can re-enter new credentials if needed.")
            else:
                messagebox.showinfo("No Credentials Found", "No credentials were found to remove.")

            # Reset UI
            self.update_credentials_ui()
            self.update_setup_status()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove credentials: {str(e)}")
            self.log_message(f"Error removing credentials: {e}")

    def update_credentials_ui(self):
        """Update the credentials UI based on current state."""
        has_credentials = self.sheets_manager.has_credentials()
        is_complete = self.sheets_manager.is_setup_complete()

        if has_credentials:
            # Hide input fields and their labels
            client_id_frame = self.client_id_entry.master
            client_secret_frame = self.client_secret_entry.master
            project_id_frame = self.project_id_entry.master

            client_id_frame.pack_forget()
            client_secret_frame.pack_forget()
            project_id_frame.pack_forget()
            self.download_button.pack_forget()

            # Show remove button
            self.remove_button.pack(side=tk.LEFT)

            # Enable/disable authenticate button
            if hasattr(self, 'dialog_auth_button'):
                if is_complete:
                    self.dialog_auth_button.config(state=tk.DISABLED, text="Already Authenticated")
                else:
                    self.dialog_auth_button.config(state=tk.NORMAL, text="Authenticate Credentials")

            # Update status
            self.update_setup_status()
        else:
            # Show input fields and their labels
            client_id_frame = self.client_id_entry.master
            client_secret_frame = self.client_secret_entry.master
            project_id_frame = self.project_id_entry.master

            client_id_frame.pack(fill=tk.X, pady=2)
            client_secret_frame.pack(fill=tk.X, pady=2)
            project_id_frame.pack(fill=tk.X, pady=2)
            self.download_button.pack(side=tk.LEFT, padx=(0, 5))

            # Hide remove button
            self.remove_button.pack_forget()

            # Disable authenticate button
            if hasattr(self, 'dialog_auth_button'):
                self.dialog_auth_button.config(state=tk.DISABLED, text="Download Credentials First")

            # Update status
            self.update_setup_status()

    def clear_sheet_url(self):
        """Clear the Google Sheet URL."""
        self.dialog_sheets_entry.delete(0, tk.END)
        self.google_sheet_url = ""
        self.google_sheet_id = ""
        self.google_sheet_name = None
        
        # Re-enable the URL entry and Set Sheet button when URL is cleared
        self.dialog_sheets_entry.config(state=tk.NORMAL)
        self.set_sheet_button.config(state=tk.NORMAL)
        
        self.save_config()
        self.log_message("Google Sheet URL cleared")
        self.update_setup_status()

    def set_sheet(self):
        """Set the Google Sheet from the entered URL/ID."""
        url_or_id = self.dialog_sheets_entry.get().strip()
        if url_or_id:
            sheet_info = self.sheets_manager.extract_sheet_info(url_or_id)
            if sheet_info['spreadsheet_id']:
                self.google_sheet_id = sheet_info['spreadsheet_id']
                self.google_sheet_name = sheet_info['sheet_name']
                self.google_sheet_url = url_or_id
                self.save_config()
                self.log_message(f"Sheet ID configured: {self.google_sheet_id}")
                if self.google_sheet_name:
                    self.log_message(f"Target sheet: {self.google_sheet_name}")
                
                # Disable the URL entry and Set Sheet button after successful configuration
                self.dialog_sheets_entry.config(state=tk.DISABLED)
                self.set_sheet_button.config(state=tk.DISABLED)
                
                # Update dialog status
                if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                    self.update_setup_status()
            else:
                self.log_message("Invalid Google Sheets URL or ID")
                if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                    self.dialog_status_label.config(text="Invalid Sheet ID/URL", fg="red")
        else:
            self.log_message("No Sheet ID/URL provided")
            if hasattr(self, 'dialog_status_label') and self.dialog_status_label.winfo_exists():
                self.dialog_status_label.config(text="Please enter Sheet ID/URL", fg="orange")

    def update_setup_status(self):
        """Update the setup status in the Google Sheets dialog."""
        if hasattr(self, 'dialog_status_label'):
            if self.sheets_manager.is_setup_complete() and self.google_sheet_id:
                self.dialog_status_label.config(text="✓ Fully configured", fg="green")
            elif self.sheets_manager.is_setup_complete():
                self.dialog_status_label.config(text="Authenticated - Set Sheet ID/URL", fg="blue")
            elif self.sheets_manager.has_credentials():
                self.dialog_status_label.config(text="Credentials available - Click Authenticate Credentials", fg="blue")
            else:
                self.dialog_status_label.config(text="Setup required - Follow instructions above", fg="orange")

    def show_settings_dialog(self):
        """Show the settings dialog for application preferences."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        try:
            dialog.iconbitmap(resource_path('syncsentinel_icon.ico'))
        except Exception:
            pass  # Icon not found, continue without it

        # Settings frame
        settings_frame = tk.LabelFrame(dialog, text="Application Settings", padx=10, pady=10)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Dark mode setting
        dark_frame = tk.Frame(settings_frame)
        dark_frame.pack(fill=tk.X, pady=5)
        self.settings_dark_var = tk.BooleanVar(value=self.dark_mode)
        dark_checkbox = tk.Checkbutton(dark_frame, text="Dark Mode", variable=self.settings_dark_var)
        dark_checkbox.pack(side=tk.LEFT)
        tk.Label(dark_frame, text="(experimental)").pack(side=tk.LEFT, padx=(5, 0))

        # Log breaks setting
        breaks_frame = tk.Frame(settings_frame)
        breaks_frame.pack(fill=tk.X, pady=5)
        self.settings_breaks_var = tk.BooleanVar(value=self.log_breaks)
        breaks_checkbox = tk.Checkbutton(breaks_frame, text="Insert breaks between log entries (CSV & Google Sheets)", 
                                       variable=self.settings_breaks_var)
        breaks_checkbox.pack(side=tk.LEFT)

        # Prepend/Append setting
        mode_frame = tk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        self.settings_mode_var = tk.BooleanVar(value=self.prepend_mode)
        mode_checkbox = tk.Checkbutton(mode_frame, text="Prepend data (uncheck for append) - CSV & Google Sheets", 
                                     variable=self.settings_mode_var)
        mode_checkbox.pack(side=tk.LEFT)

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def on_ok():
            # Apply settings
            self.dark_mode = self.settings_dark_var.get()
            self.log_breaks = self.settings_breaks_var.get()
            self.prepend_mode = self.settings_mode_var.get()
            self.save_config()
            
            # Apply dark mode if changed
            if self.dark_mode:
                self.apply_dark_mode()
            else:
                self.apply_light_mode()
            
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def apply_dark_mode(self):
        """Apply dark mode theme to the application."""
        try:
            # Dark colors
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            entry_bg = "#404040"
            button_bg = "#505050"
            
            # Apply to main window
            self.root.configure(bg=bg_color)
            
            # Apply to frames
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=bg_color)
                elif isinstance(widget, tk.Label):
                    widget.configure(bg=bg_color, fg=fg_color)
                elif isinstance(widget, tk.Button):
                    widget.configure(bg=button_bg, fg=fg_color)
                elif isinstance(widget, tk.Entry):
                    widget.configure(bg=entry_bg, fg=fg_color, insertbackground=fg_color)
                elif isinstance(widget, tk.Checkbutton):
                    widget.configure(bg=bg_color, fg=fg_color, selectcolor=button_bg)
                elif isinstance(widget, tk.Text):
                    widget.configure(bg=entry_bg, fg=fg_color, insertbackground=fg_color)
            
            # Apply to log text specifically
            if hasattr(self, 'log_text'):
                self.log_text.configure(bg=entry_bg, fg=fg_color)
                
        except Exception as e:
            self.log_message(f"Error applying dark mode: {e}")

    def apply_light_mode(self):
        """Apply light mode theme to the application."""
        try:
            # Light colors (default)
            bg_color = "SystemButtonFace"
            fg_color = "SystemWindowText"
            
            # Apply to main window
            self.root.configure(bg=bg_color)
            
            # Apply to frames and widgets
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=bg_color)
                elif isinstance(widget, tk.Label):
                    widget.configure(bg=bg_color, fg=fg_color)
                elif isinstance(widget, tk.Button):
                    widget.configure(bg="SystemButtonFace", fg=fg_color)
                elif isinstance(widget, tk.Entry):
                    widget.configure(bg="SystemWindow", fg=fg_color, insertbackground="SystemWindowText")
                elif isinstance(widget, tk.Checkbutton):
                    widget.configure(bg=bg_color, fg=fg_color, selectcolor="SystemWindow")
                elif isinstance(widget, tk.Text):
                    widget.configure(bg="SystemWindow", fg=fg_color, insertbackground="SystemWindowText")
            
            # Apply to log text specifically
            if hasattr(self, 'log_text'):
                self.log_text.configure(bg="SystemWindow", fg=fg_color)
                
        except Exception as e:
            self.log_message(f"Error applying light mode: {e}")

    def show_about(self):
        """Show the about dialog."""
        about_text = f"""SyncSentinel v{VERSION}

A comprehensive tool for monitoring and parsing FreeFileSync log files with automated CSV export and optional Google Sheets integration.

Features:
• Real-time monitoring of FreeFileSync logs
• Dual format support (.log and .html)
• CSV export with file type detection
• Google Sheets integration
• System tray support
• Cross-platform compatibility

Built with Python and Tkinter"""
        messagebox.showinfo("About SyncSentinel", about_text)


def main():
    """Main entry point."""
    print("Launching SyncSentinel GUI...")
    root = tk.Tk()
    app = MediaAssetWatcherGUI(root)
    print("GUI initialized, starting main loop...")
    root.mainloop()
    print("Application closed.")


if __name__ == "__main__":
    main()