"""
SyncSentinel Parser Module
Contains log parsing and CSV writing functionality.
"""

import re
import csv
import os


def parse_sync_log(log_file_path):
    """
    Parse a FreeFileSync log file (.log or .html format).

    Args:
        log_file_path (str): Path to the log file

    Returns:
        dict: Parsed log data with sync operations and metadata
    """
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


def append_to_csv(data, csv_file_path, prepend=False, add_breaks=False):
    """
    Append parsed log data to CSV file.

    Args:
        data (dict): Parsed log data
        csv_file_path (str): Path to CSV file
        prepend (bool): Whether to prepend data instead of append
        add_breaks (bool): Whether to add blank rows between log entries
    """
    try:
        file_exists = os.path.isfile(csv_file_path)
        file_is_empty = file_exists and os.path.getsize(csv_file_path) == 0
        
        # Prepare new rows
        fieldnames = ['Date', 'Time', 'Type', 'Section', 'File Name']
        new_rows = []

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

        # Create new rows
        for file_name, info in unique_files.items():
            new_rows.append({
                'Date': data['date'],
                'Time': info['timestamp'],
                'Type': info['file_type'],
                'Section': info['section'],
                'File Name': info['file_name']
            })
        
        # Add break row if requested
        if add_breaks:
            new_rows.append({'Date': '--- New Log Entry ---', 'Time': '', 'Type': '', 'Section': '', 'File Name': ''})

        if prepend and file_exists and not file_is_empty:
            # Read existing content
            existing_rows = []
            with open(csv_file_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_rows.append(row)
            
            # Write new content with new data first
            with open(csv_file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                # Write new rows first
                for row in new_rows:
                    writer.writerow(row)
                # Write existing rows
                for row in existing_rows:
                    writer.writerow(row)
        else:
            # Append mode or new file or empty file
            with open(csv_file_path, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists or file_is_empty:
                    writer.writeheader()
                # Write new rows
                for row in new_rows:
                    writer.writerow(row)

    except Exception as e:
        print(f"Error in append_to_csv: {e}")
        import traceback
        print(f"CSV append traceback: {traceback.format_exc()}")
        raise


def get_file_type(extension):
    """
    Get file type based on extension.

    Args:
        extension (str): File extension (e.g., '.png')

    Returns:
        str: File type category
    """
    # Define file type mappings
    file_types = {
        'Image': ['.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.tif', '.exr', '.tga', '.dpx'],
        'Video': ['.mov'],
        'Audio': ['.mp3', '.wav', '.aiff'],
        '3D': ['.abc', '.fbx', '.obj']
    }

    for type_name, exts in file_types.items():
        if extension.lower() in exts:
            return type_name
    return 'Unknown'


def extract_unique_files(parsed_data):
    """
    Extract unique files from parsed data with metadata.

    Args:
        parsed_data (dict): Parsed log data

    Returns:
        dict: Dictionary of unique files with metadata
    """
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

    return unique_files