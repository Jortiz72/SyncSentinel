"""
SyncSentinel Handler Module
Contains file system event handling for log file monitoring.
"""

import time
import traceback
from watchdog.events import FileSystemEventHandler


class LogFileHandler(FileSystemEventHandler):
    """
    File system event handler for monitoring log file creation.
    """

    def __init__(self, csv_file_path, log_callback, store_callback, sheets_callback=None, prepend=False, add_breaks=False):
        """
        Initialize the handler.

        Args:
            csv_file_path (str): Path to CSV output file
            log_callback (callable): Function to log messages
            store_callback (callable): Function to store parsed data
            sheets_callback (callable, optional): Function to upload to Google Sheets
            prepend (bool): Whether to prepend data to CSV instead of append
            add_breaks (bool): Whether to add breaks between log entries in CSV
        """
        self.csv_file_path = csv_file_path
        self.log_callback = log_callback
        self.store_callback = store_callback
        self.sheets_callback = sheets_callback
        self.prepend = prepend
        self.add_breaks = add_breaks

    def on_created(self, event):
        """
        Handle file creation events.

        Args:
            event: File system event
        """
        if not event.is_directory and (event.src_path.endswith('.log') or event.src_path.endswith('.html')):
            try:
                self.log_callback(f"New log file detected: {event.src_path}")

                # Check if file is ready to be read (not still being written)
                time.sleep(0.5)  # Wait a bit for file to be fully written

                from syncsentinel.parser import parse_sync_log, append_to_csv
                parsed_data = parse_sync_log(event.src_path)
                self.log_callback(f"Successfully parsed log file: {len(parsed_data.get('sync_operations', []))} operations found")

                append_to_csv(parsed_data, self.csv_file_path, prepend=self.prepend, add_breaks=self.add_breaks)

                self.store_callback(parsed_data)
                self.log_callback("Data stored for clipboard access")

                # Upload to Google Sheets if callback provided
                if self.sheets_callback:
                    self.sheets_callback(parsed_data)

            except Exception as e:
                self.log_callback(f"Error processing new log file {event.src_path}: {e}")
                self.log_callback(f"Traceback: {traceback.format_exc()}")