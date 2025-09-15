"""
SyncSentinel Google Sheets Integration Module
Handles Google Sheets API authentication and data upload.
"""

import os
import pickle
import json
import base64
import secrets
import platform
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsManager:
    """
    Manages Google Sheets authentication and data operations.
    """

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    TOKEN_FILE = 'token.pickle'
    CREDENTIALS_FILE = 'credentials.json'
    ENCRYPTED_CREDENTIALS_FILE = 'credentials.enc'
    KEY_FILE = 'credentials.key'

    def __init__(self):
        """Initialize the Google Sheets manager."""
        # Use proper Windows AppData location for user data
        if platform.system() == 'Windows':
            self.base_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SyncSentinel')
        else:
            # For other platforms, use home directory
            self.base_dir = os.path.join(os.path.expanduser('~'), '.syncsentinel')
        os.makedirs(self.base_dir, exist_ok=True)
        self.TOKEN_FILE = os.path.join(self.base_dir, 'token.pickle')
        self.CREDENTIALS_FILE = os.path.join(self.base_dir, 'credentials.json')
        self.ENCRYPTED_CREDENTIALS_FILE = os.path.join(self.base_dir, 'credentials.enc')
        self.KEY_FILE = os.path.join(self.base_dir, 'credentials.key')
        
        self.creds = None
        self.service = None
        self.encryption_key = None
        self._load_encryption_key()

    def _load_encryption_key(self):
        """Load or generate encryption key."""
        try:
            if os.path.exists(self.KEY_FILE):
                with open(self.KEY_FILE, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                # Generate a new key
                salt = secrets.token_bytes(16)
                password = secrets.token_hex(32).encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                self.encryption_key = base64.urlsafe_b64encode(kdf.derive(password))

                # Save the key
                with open(self.KEY_FILE, 'wb') as f:
                    f.write(self.encryption_key)
        except Exception as e:
            print(f"Error loading encryption key: {e}")
            # Fallback to a simple key for basic functionality
            self.encryption_key = Fernet.generate_key()

    def _encrypt_credentials(self, credentials_data):
        """Encrypt credentials data."""
        try:
            fernet = Fernet(self.encryption_key)
            json_data = json.dumps(credentials_data).encode()
            encrypted_data = fernet.encrypt(json_data)
            return encrypted_data
        except Exception as e:
            print(f"Error encrypting credentials: {e}")
            return None

    def _decrypt_credentials(self):
        """Decrypt credentials data."""
        try:
            if not os.path.exists(self.ENCRYPTED_CREDENTIALS_FILE):
                return None

            with open(self.ENCRYPTED_CREDENTIALS_FILE, 'rb') as f:
                encrypted_data = f.read()

            fernet = Fernet(self.encryption_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            credentials_data = json.loads(decrypted_data.decode())
            return credentials_data
        except Exception as e:
            print(f"Error decrypting credentials: {e}")
            return None

    def download_credentials(self, client_id, client_secret, project_id):
        """
        Automatically download and setup credentials from Google Cloud Console.

        Args:
            client_id (str): OAuth client ID
            client_secret (str): OAuth client secret
            project_id (str): Google Cloud project ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create credentials JSON structure
            credentials_data = {
                "installed": {
                    "client_id": client_id,
                    "project_id": project_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"]
                }
            }

            # Encrypt and save credentials
            encrypted_data = self._encrypt_credentials(credentials_data)
            if encrypted_data:
                with open(self.ENCRYPTED_CREDENTIALS_FILE, 'wb') as f:
                    f.write(encrypted_data)

                # Also save unencrypted version for Google API compatibility
                with open(self.CREDENTIALS_FILE, 'w') as f:
                    json.dump(credentials_data, f, indent=2)

                return True
            return False

        except Exception as e:
            print(f"Error downloading credentials: {e}")
            return False

    def has_credentials(self):
        """Check if credentials are available."""
        return (os.path.exists(self.CREDENTIALS_FILE) or
                os.path.exists(self.ENCRYPTED_CREDENTIALS_FILE))

    def get_setup_instructions(self):
        """Get setup instructions for Google Sheets integration."""
        return {
            'title': 'Google Sheets Setup',
            'steps': [
                '1. Go to Google Cloud Console: https://console.cloud.google.com/',
                '2. Create a new project or select existing one',
                '3. Enable Google Sheets API',
                '4. Create OAuth 2.0 credentials (Desktop application)',
                '5. Copy your Client ID and Client Secret below',
                '6. Enter your Project ID',
                '7. Click "Download Credentials" to complete setup'
            ],
            'fields': ['client_id', 'client_secret', 'project_id']
        }

    def authenticate(self):
        """
        Authenticate with Google Sheets API.

        Returns:
            tuple: (bool, str) - Success status and error message if failed
        """
        try:
            # Load existing credentials
            if os.path.exists(self.TOKEN_FILE):
                with open(self.TOKEN_FILE, 'rb') as token:
                    self.creds = pickle.load(token)

            # If there are no (valid) credentials available, let the user log in
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    # Try to load credentials from encrypted file if regular file doesn't exist
                    if not os.path.exists(self.CREDENTIALS_FILE):
                        if os.path.exists(self.ENCRYPTED_CREDENTIALS_FILE):
                            credentials_data = self._decrypt_credentials()
                            if credentials_data:
                                with open(self.CREDENTIALS_FILE, 'w') as f:
                                    json.dump(credentials_data, f, indent=2)
                            else:
                                return False, "Failed to decrypt credentials"
                        else:
                            return False, "No credentials found. Please complete the setup process first."

                    flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_FILE, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(self.TOKEN_FILE, 'wb') as token:
                    pickle.dump(self.creds, token)

            # Build the service
            self.service = build('sheets', 'v4', credentials=self.creds)
            return True, "Authentication successful"

        except Exception as e:
            return False, f"Authentication failed: {str(e)}"

    def is_setup_complete(self):
        """Check if Google Sheets setup is complete."""
        return (os.path.exists(self.CREDENTIALS_FILE) or
                os.path.exists(self.ENCRYPTED_CREDENTIALS_FILE)) and \
               os.path.exists(self.TOKEN_FILE)

    def upload_data(self, spreadsheet_id, data, sheet_name=None, prepend=True, add_breaks=False):
        """
        Upload parsed log data to Google Sheets.

        Args:
            spreadsheet_id (str): Google Sheets spreadsheet ID
            data (dict): Parsed log data
            sheet_name (str): Optional sheet name to target
            prepend (bool): Whether to prepend (True) or append (False) data
            add_breaks (bool): Whether to add breaks between log entries

        Returns:
            tuple: (bool, str) - Success status and error message if failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return False, "Failed to authenticate with Google Sheets"

            # Extract data for upload
            from parser import extract_unique_files
            unique_files = extract_unique_files(data)

            if not unique_files:
                return False, "No data to upload - no files found in parsed data"

            # Prepare data for Google Sheets
            headers = ['Date', 'Time', 'Type', 'Section', 'File Name']
            new_rows = []

            for file_name, info in unique_files.items():
                row = [
                    data['date'],
                    info['timestamp'],
                    info['file_type'],
                    info['section'],
                    info['file_name']
                ]
                new_rows.append(row)

            # Calculate total rows to insert (new data + break if enabled)
            num_new_rows = len(new_rows)
            if add_breaks:
                num_new_rows += 1  # Add space for break row

            # Resolve sheet name if provided
            actual_sheet_name = None
            if sheet_name:
                if sheet_name.startswith('gid_'):
                    resolved_name = self.resolve_sheet_name(spreadsheet_id, sheet_name)
                    if resolved_name:
                        actual_sheet_name = resolved_name
                    else:
                        # If we can't resolve the gid, fall back to first sheet
                        available_sheets = self.get_sheet_names(spreadsheet_id)
                        if available_sheets:
                            actual_sheet_name = available_sheets[0]
                else:
                    actual_sheet_name = sheet_name

            # Get sheet ID for batchUpdate operations
            sheet_id = None
            if actual_sheet_name:
                try:
                    spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                    sheets = spreadsheet.get('sheets', [])
                    for sheet in sheets:
                        properties = sheet.get('properties', {})
                        if properties.get('title') == actual_sheet_name:
                            sheet_id = properties.get('sheetId')
                            break
                except Exception as e:
                    print(f"Warning: Could not get sheet ID for {actual_sheet_name}: {e}")

            # Check if sheet has data and handle empty sheets
            range_name = f"'{actual_sheet_name}'!A:A" if actual_sheet_name else "A:A"
            try:
                existing_data = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                existing_values = existing_data.get('values', [])
                has_header = len(existing_values) > 0 and existing_values[0]
            except Exception:
                # Sheet might be empty or not exist
                has_header = False
                existing_values = []

            # Add header if sheet is empty
            if not has_header:
                try:
                    header_body = {'values': [headers]}
                    header_range = f"'{actual_sheet_name}'!A1:E1" if actual_sheet_name else "A1:E1"
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=header_range,
                        valueInputOption='RAW',
                        body=header_body
                    ).execute()
                    existing_values = [headers]  # Update our local copy
                except Exception as e:
                    return False, f"Failed to add header to sheet: {str(e)}"

            if prepend:
                # Use insertDimension to shift all existing rows down (including checkboxes in column F)
                if sheet_id is not None and num_new_rows > 0:
                    try:
                        # Insert rows after header (startIndex=1)
                        insert_request = {
                            'insertDimension': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'dimension': 'ROWS',
                                    'startIndex': 1,  # After header row
                                    'endIndex': 1 + num_new_rows
                                },
                                'inheritFromBefore': False
                            }
                        }

                        batch_update_body = {'requests': [insert_request]}
                        self.service.spreadsheets().batchUpdate(
                            spreadsheetId=spreadsheet_id,
                            body=batch_update_body
                        ).execute()

                        # Now write the new data to the inserted rows
                        all_new_data = new_rows.copy()
                        if add_breaks:
                            all_new_data.append(['--- New Log Entry ---', '', '', '', ''])

                        insert_body = {'values': all_new_data}
                        insert_range = f"'{actual_sheet_name}'!A2:E{1 + len(all_new_data)}" if actual_sheet_name else f"A2:E{1 + len(all_new_data)}"

                        self.service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=insert_range,
                            valueInputOption='RAW',
                            body=insert_body
                        ).execute()

                        return True, f"Successfully prepended {len(new_rows)} rows to Google Sheets (sheet: {actual_sheet_name or 'default'})"

                    except Exception as e:
                        print(f"Insert dimension failed, falling back to manual method: {e}")
                        # Fall back to the old method if insertDimension fails

                # Fallback: Manual prepend method (old approach)
                try:
                    # Read existing data (excluding header)
                    existing_data_range = f"'{actual_sheet_name}'!A2:E" if actual_sheet_name else "A2:E"
                    existing_data_result = self.service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=existing_data_range
                    ).execute()
                    existing_rows = existing_data_result.get('values', [])

                    # Insert new data at row 2
                    all_new_data = new_rows.copy()
                    if add_breaks:
                        all_new_data.append(['--- New Log Entry ---', '', '', '', ''])

                    insert_body = {'values': all_new_data}
                    insert_range = f"'{actual_sheet_name}'!A2:E{1 + len(all_new_data)}" if actual_sheet_name else f"A2:E{1 + len(all_new_data)}"

                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=insert_range,
                        valueInputOption='RAW',
                        body=insert_body
                    ).execute()

                    # Write existing data after the new data
                    if existing_rows:
                        existing_body = {'values': existing_rows}
                        existing_start_row = 2 + len(all_new_data)
                        existing_insert_range = f"'{actual_sheet_name}'!A{existing_start_row}:E{existing_start_row - 1 + len(existing_rows)}" if actual_sheet_name else f"A{existing_start_row}:E{existing_start_row - 1 + len(existing_rows)}"

                        self.service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=existing_insert_range,
                            valueInputOption='RAW',
                            body=existing_body
                        ).execute()

                    return True, f"Successfully prepended {len(new_rows)} rows to Google Sheets (sheet: {actual_sheet_name or 'default'})"

                except Exception as e:
                    return False, f"Failed to prepend data: {str(e)}"

            else:
                # Append mode - find the last row and add data there
                try:
                    last_row = len(existing_values) + 1

                    # Add break row if enabled and there's existing data beyond header
                    if add_breaks and len(existing_values) > 1:  # More than just header
                        break_body = {'values': [['--- New Log Entry ---', '', '', '', '']]}
                        break_range = f"'{actual_sheet_name}'!A{last_row}:E{last_row}" if actual_sheet_name else f"A{last_row}:E{last_row}"
                        self.service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=break_range,
                            valueInputOption='RAW',
                            body=break_body
                        ).execute()
                        last_row += 1

                    # Append new data
                    insert_body = {'values': new_rows}
                    insert_range = f"'{actual_sheet_name}'!A{last_row}:E{last_row - 1 + len(new_rows)}" if actual_sheet_name else f"A{last_row}:E{last_row - 1 + len(new_rows)}"

                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=insert_range,
                        valueInputOption='RAW',
                        body=insert_body
                    ).execute()

                    return True, f"Successfully appended {len(new_rows)} rows to Google Sheets (sheet: {actual_sheet_name or 'default'})"

                except Exception as e:
                    return False, f"Failed to append data: {str(e)}"

        except HttpError as e:
            error_details = f"Google Sheets API error: {e}"
            if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                error_details += f" (HTTP {e.resp.status})"
            return False, error_details
        except Exception as e:
            return False, f"Upload failed: {str(e)}"

    def get_sheet_names(self, spreadsheet_id):
        """
        Get all sheet names from a Google Sheets spreadsheet.

        Args:
            spreadsheet_id (str): Google Sheets spreadsheet ID

        Returns:
            list: List of sheet names, or None if failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None

            # Get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])

            sheet_names = []
            for sheet in sheets:
                properties = sheet.get('properties', {})
                title = properties.get('title')
                if title:
                    sheet_names.append(title)

            return sheet_names

        except Exception as e:
            print(f"Failed to get sheet names: {e}")
            return None

    def resolve_sheet_name(self, spreadsheet_id, sheet_identifier):
        """
        Resolve a sheet identifier (name or gid) to an actual sheet name.

        Args:
            spreadsheet_id (str): Google Sheets spreadsheet ID
            sheet_identifier (str): Sheet name or gid marker (e.g., "gid_123456")

        Returns:
            str: Actual sheet name, or None if not found
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None

            # If it's already a regular sheet name (not a gid marker), return as-is
            if not sheet_identifier.startswith('gid_'):
                return sheet_identifier

            # Extract gid from marker
            gid = sheet_identifier.split('_')[1]

            # Get spreadsheet metadata to find the sheet with matching gid
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])

            for sheet in sheets:
                properties = sheet.get('properties', {})
                sheet_gid = properties.get('sheetId')
                title = properties.get('title')

                if str(sheet_gid) == gid and title:
                    return title

            return None

        except Exception as e:
            print(f"Failed to resolve sheet name for {sheet_identifier}: {e}")
            return None

    def extract_sheet_info(self, url_or_id):
        """
        Extract spreadsheet ID and sheet name/ID from URL or return ID if already provided.

        Args:
            url_or_id (str): Google Sheets URL or ID

        Returns:
            dict: {'spreadsheet_id': str, 'sheet_name': str or None}
        """
        spreadsheet_id = None
        sheet_name = None

        if '/' in url_or_id:
            # Extract from URL
            if 'docs.google.com/spreadsheets' in url_or_id:
                # URL format: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit#gid=SHEET_ID
                parts = url_or_id.split('/')
                try:
                    id_index = parts.index('d') + 1
                    spreadsheet_id = parts[id_index]

                    # Check for sheet ID in URL fragment
                    if '#' in url_or_id:
                        fragment = url_or_id.split('#')[-1]
                        if fragment.startswith('gid='):
                            # For gid, we can't reliably determine the sheet name without API call
                            # Store the gid for now, we'll resolve it later if needed
                            gid = fragment.split('=')[-1]
                            sheet_name = f"gid_{gid}"  # Special marker for gid-based sheets
                        elif fragment:
                            sheet_name = fragment
                except (ValueError, IndexError):
                    pass
        else:
            # Assume it's already an ID
            spreadsheet_id = url_or_id

        return {
            'spreadsheet_id': spreadsheet_id,
            'sheet_name': sheet_name
        }