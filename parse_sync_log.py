import re
import json
import csv
import os
import threading
import subprocess
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import platform
from pystray import Icon, Menu, MenuItem
from PIL import Image

def parse_sync_log(log_file_path):
    with open(log_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if log_file_path.lower().endswith('.html'):
        # Parse HTML format
        data = {
            'sync_name': None,
            'date': None,
            'start_time': None,
            'items_processed': None,
            'total_size': None,
            'total_time': None,
            'comparison_items': None,
            'comparison_time': None,
            'sync_operations': []
        }
        
        # Extract sync name
        name_match = re.search(r'<span style="font-weight:600; color:gray;">([^<]+)</span>', content)
        if name_match:
            data['sync_name'] = name_match.group(1)
        
        # Extract date
        date_match = re.search(r'(\d+/\d+/\d+)', content)
        if date_match:
            data['date'] = date_match.group(1)
        
        # Extract start time
        time_match = re.search(r'(\d+:\d+:\d+ \w+)</span>', content)
        if time_match:
            data['start_time'] = time_match.group(1)
        
        # Extract file creations
        timestamps = re.findall(r'<td valign="top">(\d+:\d+:\d+ \w+)</td>', content)
        file_paths = re.findall(r'Creating file &quot;([^&]+)&quot;', content)
        
        files_created = []
        for ts, fp in zip(timestamps, file_paths):
            files_created.append({
                'timestamp': ts,
                'file_path': fp
            })
        
        # Assume one operation
        data['sync_operations'].append({
            'source': '',
            'destination': '',
            'files_created': files_created
        })
        
    else:
        # Parse LOG format
        lines = content.splitlines()
        
        data = {
            'sync_name': None,
            'date': None,
            'start_time': None,
            'items_processed': None,
            'total_size': None,
            'total_time': None,
            'comparison_items': None,
            'comparison_time': None,
            'sync_operations': []
        }

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Parse header
            match = re.match(r"(.+) (\d+/\d+/\d+) \[(\d+:\d+:\d+ \w+)\]", line)
            if match:
                data['sync_name'] = match.group(1)
                data['date'] = match.group(2)
                data['start_time'] = match.group(3)
                i += 1
                continue

            # Parse summary
            if line.startswith('|    Items processed:'):
                match = re.search(r'Items processed: (\d+) \(([\d.]+ \w+)\)', line)
                if match:
                    data['items_processed'] = int(match.group(1))
                    data['total_size'] = match.group(2)
            elif line.startswith('|    Total time:'):
                match = re.search(r'Total time: (\d+:\d+:\d+)', line)
                if match:
                    data['total_time'] = match.group(1)

            # Parse comparison
            match = re.search(r'Info:\s+Comparison finished: ([\d,]+) items found – Time elapsed: (\d+:\d+:\d+)', line)
            if match:
                data['comparison_items'] = int(match.group(1).replace(',', ''))
                data['comparison_time'] = match.group(2)
                i += 1
                continue

            # Parse synchronizing folder pair
            if 'Synchronizing folder pair: Update >' in line:
                # Next line is source, next next is dest
                if i + 2 < len(lines):
                    source = lines[i + 1].strip()
                    dest = lines[i + 2].strip()
                    current_operation = {
                        'source': source,
                        'destination': dest,
                        'files_created': []
                    }
                    data['sync_operations'].append(current_operation)
                    i += 3  # Skip the next two lines
                    continue

            # Parse creating file
            match = re.search(r'Info:\s+Creating file "(.+)"', line)
            if match and data['sync_operations']:
                file_path = match.group(1)
                # Extract timestamp
                time_match = re.match(r'\[(\d+:\d+:\d+ \w+)\]', line)
                if time_match:
                    timestamp = time_match.group(1)
                    data['sync_operations'][-1]['files_created'].append({
                        'timestamp': timestamp,
                        'file_path': file_path
                    })
            i += 1
    
    return data

def append_to_csv(data, csv_file_path):
    try:
        # Define file type mappings
        file_types = {
            'Image': ['.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.tif', '.exr', '.tga', '.dpx'],
            'Video': ['.mov'],
            'Audio': ['.mp3', '.wav', '.aiff'],
            '3D': ['.abc', '.fbx', '.obj']
        }

        def get_file_type(extension):
            for type_name, exts in file_types.items():
                if extension.lower() in exts:
                    return type_name
            return 'Unknown'

        file_exists = os.path.isfile(csv_file_path)
        print(f"Appending to CSV: {csv_file_path}, file exists: {file_exists}")

        with open(csv_file_path, 'a', newline='') as csvfile:
            fieldnames = ['Date', 'Time', 'Type', 'Section', 'File Name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                print("CSV header written")

            # Collect unique files
            unique_files = {}
            for operation in data['sync_operations']:
                for file_info in operation['files_created']:
                    file_path = file_info['file_path']
                    # Extract file name
                    file_name = file_path.split('\\')[-1]
                    if file_name not in unique_files:
                        # Extract extension
                        extension = '.' + file_name.split('.')[-1] if '.' in file_name else ''
                        # Get type
                        file_type = get_file_type(extension)
                        # Extract section
                        path_parts = file_path.split('\\')
                        try:
                            video_file_index = path_parts.index('VideoFile')
                            section = path_parts[video_file_index + 1] if video_file_index + 1 < len(path_parts) else ''
                        except ValueError:
                            section = ''

                        unique_files[file_name] = {
                            'timestamp': file_info['timestamp'],
                            'file_type': file_type,
                            'section': section,
                            'file_name': file_name
                        }

            # Write unique files
            rows_written = 0
            for file_name, info in unique_files.items():
                writer.writerow({
                    'Date': data['date'],
                    'Time': info['timestamp'],
                    'Type': info['file_type'],
                    'Section': info['section'],
                    'File Name': info['file_name']
                })
                rows_written += 1

            print(f"Successfully wrote {rows_written} rows to CSV")

    except Exception as e:
        print(f"Error in append_to_csv: {e}")
        import traceback
        print(f"CSV append traceback: {traceback.format_exc()}")
        raise

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, csv_file_path, log_callback, store_callback):
        self.csv_file_path = csv_file_path
        self.log_callback = log_callback
        self.store_callback = store_callback

    def on_created(self, event):
        if not event.is_directory and (event.src_path.endswith('.log') or event.src_path.endswith('.html')):
            try:
                self.log_callback(f"New log file detected: {event.src_path}")

                # Check if file is ready to be read (not still being written)
                import time
                time.sleep(0.5)  # Wait a bit for file to be fully written

                parsed_data = parse_sync_log(event.src_path)
                self.log_callback(f"Successfully parsed log file: {len(parsed_data.get('sync_operations', []))} operations found")

                append_to_csv(parsed_data, self.csv_file_path)

                self.store_callback(parsed_data)
                self.log_callback(f"Data stored for clipboard access")

            except Exception as e:
                self.log_callback(f"Error processing new log file {event.src_path}: {e}")
                import traceback
                self.log_callback(f"Traceback: {traceback.format_exc()}")

class MediaAssetWatcherGUI:
    def __init__(self, root):
        print("SyncSentinel starting...")
        self.root = root
        self.root.title("SyncSentinel")
        self.root.geometry("900x575")
        
        self.watching = False
        self.observer = None
        self.watch_path = ""
        self.csv_file = ""
        self.last_parsed_data = None
        self.last_parsed_date = None
        
        # Folder selection
        self.folder_frame = tk.Frame(root)
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
        self.csv_frame = tk.Frame(root)
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
        
        # Control buttons
        self.button_frame = tk.Frame(root)
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
        self.log_label = tk.Label(root, text="Activity Log:")
        self.log_label.pack(anchor=tk.W, padx=10)
        
        # Create a frame for the log text with scrollbars
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        # Create text widget with no wrap
        self.log_text = tk.Text(self.log_frame, width=70, height=15, wrap=tk.NONE)
        
        # Create vertical scrollbar
        self.v_scrollbar = tk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=self.v_scrollbar.set)
        
        # Create horizontal scrollbar
        self.h_scrollbar = tk.Scrollbar(self.log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.config(xscrollcommand=self.h_scrollbar.set)
        
        # Pack the widgets
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        self.v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        # Configure grid weights
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        # Bind entries change
        self.folder_entry.bind('<KeyRelease>', self.check_inputs)
        self.csv_entry.bind('<KeyRelease>', self.check_inputs)
        self.csv_entry.bind('<FocusOut>', self.add_csv_extension)
        
        # Check inputs initially to enable buttons if defaults are valid
        self.check_inputs()
    
    def setup_tray_icon(self):
        """Setup system tray icon."""
        try:
            # Load icon
            if os.path.exists('syncsentinel_icon.png'):
                image = Image.open('syncsentinel_icon.png')
            else:
                # Create a default icon
                image = Image.new('RGB', (64, 64), color='blue')
            
            # Create menu
            menu = Menu(
                MenuItem('Show', self.show_window),
                MenuItem('Quit', self.quit_app)
            )
            
            # Create tray icon
            self.tray_icon = Icon('SyncSentinel', image, 'SyncSentinel', menu)
            self.tray_icon.run_detached()
            
        except Exception as e:
            self.log_message(f"Failed to setup tray icon: {e}")
    
    def show_window(self, icon, item):
        """Show the main window from tray."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def quit_app(self, icon, item):
        """Quit the application from tray."""
        self.stop_watching()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.quit()
    
    def minimize_to_tray(self):
        """Minimize window to system tray instead of closing."""
        self.root.withdraw()
        self.log_message("Application minimized to system tray")
    
    def set_folder(self):
        current_path = self.folder_entry.get()
        initial_dir = current_path if os.path.isdir(current_path) else None
        folder = filedialog.askdirectory(initialdir=initial_dir)
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.check_inputs()
    
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
    
    def store_last_parsed(self, parsed_data):
        try:
            print(f"store_last_parsed called with date: {parsed_data.get('date', 'NO_DATE')}")
            print(f"Operations found: {len(parsed_data.get('sync_operations', []))}")

            # Define file type mappings
            file_types = {
                'Image': ['.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.tif', '.exr', '.tga', '.dpx'],
                'Video': ['.mov'],
                'Audio': ['.mp3', '.wav', '.aiff'],
                '3D': ['.abc', '.fbx', '.obj']
            }

            def get_file_type(extension):
                for type_name, exts in file_types.items():
                    if extension.lower() in exts:
                        return type_name
                return 'Unknown'

            unique_files = {}
            for operation in parsed_data['sync_operations']:
                for file_info in operation['files_created']:
                    file_path = file_info['file_path']
                    # Extract file name
                    file_name = file_path.split('\\')[-1]
                    if file_name not in unique_files:
                        # Extract extension
                        extension = '.' + file_name.split('.')[-1] if '.' in file_name else ''
                        # Get type
                        file_type = get_file_type(extension)
                        # Extract section
                        path_parts = file_path.split('\\')
                        try:
                            video_file_index = path_parts.index('VideoFile')
                            section = path_parts[video_file_index + 1] if video_file_index + 1 < len(path_parts) else ''
                        except ValueError:
                            section = ''

                        unique_files[file_name] = {
                            'timestamp': file_info['timestamp'],
                            'file_type': file_type,
                            'section': section,
                            'file_name': file_name
                        }

            self.last_parsed_data = unique_files
            self.last_parsed_date = parsed_data['date']
            self.copy_button.config(state=tk.NORMAL)
            self.log_message(f"Stored {len(unique_files)} unique files from last parsed log")
            print(f"Successfully stored {len(unique_files)} files for clipboard access")

        except Exception as e:
            print(f"Error in store_last_parsed: {e}")
            import traceback
            print(f"Store traceback: {traceback.format_exc()}")
            self.log_message(f"Error storing parsed data: {e}")

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
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
        try:
            if self.last_parsed_data and self.last_parsed_date:
                # Format the data as tab-separated text without headers
                output = []

                for file_name, info in self.last_parsed_data.items():
                    row = [
                        self.last_parsed_date,
                        info['timestamp'],
                        info['file_type'],
                        info['section'],
                        info['file_name']
                    ]
                    output.append('\t'.join(row))

                tsv_text = '\n'.join(output)

                # Try tkinter clipboard first
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(tsv_text)
                    self.log_message(f"Copied {len(output)} entries to clipboard")
                except Exception as tk_error:
                    # Fallback to Windows clipboard if tkinter fails
                    self.log_message(f"Tkinter clipboard failed: {tk_error}, trying Windows clipboard...")
                    try:
                        import subprocess
                        # Use Windows clip command
                        process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                        process.communicate(tsv_text.encode('utf-16'))
                        self.log_message(f"Copied {len(output)} entries to clipboard (Windows fallback)")
                    except Exception as win_error:
                        self.log_message(f"Windows clipboard also failed: {win_error}")
                        messagebox.showerror("Error", f"Failed to copy to clipboard: {tk_error}")
            else:
                messagebox.showinfo("Info", "No log data available to copy")
        except Exception as e:
            self.log_message(f"Error in copy_last_log: {e}")
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")

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
        event_handler = LogFileHandler(self.csv_file, self.log_message, self.store_last_parsed)
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
        
        # Get list of log files
        log_files = [f for f in os.listdir(self.watch_path) if f.endswith(('.log', '.html'))]
        
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
                    append_to_csv(parsed_data, self.csv_file)
                    self.store_last_parsed(parsed_data)
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

if __name__ == "__main__":
    print("Launching SyncSentinel GUI...")
    root = tk.Tk()
    app = MediaAssetWatcherGUI(root)
    print("GUI initialized, starting main loop...")
    root.mainloop()
    print("Application closed.")
