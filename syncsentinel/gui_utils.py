"""
SyncSentinel GUI Utilities Module
Contains GUI-specific helper functions and data processing.
"""

import datetime
import os
import sys
import traceback


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def store_last_parsed(gui_instance, parsed_data):
    """
    Store parsed data for clipboard access and enable copy button.

    Args:
        gui_instance: GUI instance with required attributes
        parsed_data (dict): Parsed log data
    """
    try:
        print(f"store_last_parsed called with date: {parsed_data.get('date', 'NO_DATE')}")
        print(f"Operations found: {len(parsed_data.get('sync_operations', []))}")

        from syncsentinel.parser import extract_unique_files
        unique_files = extract_unique_files(parsed_data)

        gui_instance.last_parsed_data = unique_files
        gui_instance.last_parsed_date = parsed_data['date']
        gui_instance.copy_button.config(state='normal')
        gui_instance.log_message(f"Stored {len(unique_files)} unique files from last parsed log")
        print(f"Successfully stored {len(unique_files)} files for clipboard access")

    except Exception as e:
        print(f"Error in store_last_parsed: {e}")
        print(f"Store traceback: {traceback.format_exc()}")
        gui_instance.log_message(f"Error storing parsed data: {e}")


def log_message(gui_instance, message):
    """
    Log a message to the GUI's log text area.

    Args:
        gui_instance: GUI instance with log_text attribute
        message (str): Message to log
    """
    if hasattr(gui_instance, 'log_text') and gui_instance.log_text:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        gui_instance.log_text.insert('end', f"[{timestamp}] {message}\n")
        gui_instance.log_text.see('end')
    else:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def copy_last_log(gui_instance):
    """
    Copy the last parsed log data to clipboard.

    Args:
        gui_instance: GUI instance with clipboard and data attributes
    """
    try:
        if gui_instance.last_parsed_data and gui_instance.last_parsed_date:
            # Format the data as tab-separated text without headers
            output = []

            for file_name, info in gui_instance.last_parsed_data.items():
                row = [
                    gui_instance.last_parsed_date,
                    info['timestamp'],
                    info['file_type'],
                    info['section'],
                    info['file_name']
                ]
                output.append('\t'.join(row))

            tsv_text = '\n'.join(output)

            # Try tkinter clipboard first
            try:
                gui_instance.root.clipboard_clear()
                gui_instance.root.clipboard_append(tsv_text)
                gui_instance.log_message(f"Copied {len(output)} entries to clipboard")
            except Exception as tk_error:
                # Fallback to Windows clipboard if tkinter fails
                gui_instance.log_message(f"Tkinter clipboard failed: {tk_error}, trying Windows clipboard...")
                try:
                    import subprocess
                    # Use Windows clip command
                    process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                    process.communicate(tsv_text.encode('utf-16'))
                    gui_instance.log_message(f"Copied {len(output)} entries to clipboard (Windows fallback)")
                except Exception as win_error:
                    gui_instance.log_message(f"Windows clipboard also failed: {win_error}")
                    import tkinter.messagebox as messagebox
                    messagebox.showerror("Error", f"Failed to copy to clipboard: {tk_error}")
        else:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Info", "No log data available to copy")
    except Exception as e:
        gui_instance.log_message(f"Error in copy_last_log: {e}")
        import tkinter.messagebox as messagebox
        messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")


def setup_tray_icon(gui_instance):
    """
    Setup system tray icon for the application.

    Args:
        gui_instance: GUI instance
    """
    try:
        # Load icon
        icon_path = resource_path('syncsentinel_icon.png')
        if os.path.exists(icon_path):
            from PIL import Image
            image = Image.open(icon_path)
        else:
            # Create a default icon
            from PIL import Image
            image = Image.new('RGB', (64, 64), color='blue')

        # Create menu
        from pystray import Menu, MenuItem, Icon
        menu = Menu(
            MenuItem('Show', gui_instance.show_window, default=True),
            MenuItem('Quit', gui_instance.quit_app)
        )

        # Create tray icon
        gui_instance.tray_icon = Icon('SyncSentinel', image, 'SyncSentinel', menu)
        gui_instance.tray_icon.run_detached()

    except Exception as e:
        gui_instance.log_message(f"Failed to setup tray icon: {e}")


def show_window(gui_instance, icon, item):
    """Show the main window from tray."""
    gui_instance.root.deiconify()
    gui_instance.root.lift()
    gui_instance.root.focus_force()


def quit_app(gui_instance, icon, item):
    """Quit the application from tray."""
    gui_instance.stop_watching()
    if hasattr(gui_instance, 'tray_icon'):
        gui_instance.tray_icon.stop()
    gui_instance.root.quit()


def minimize_to_tray(gui_instance):
    """Minimize window to system tray instead of closing."""
    gui_instance.root.withdraw()
    gui_instance.log_message("Application minimized to system tray")