import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from time import sleep

SCOPES = st.secrets['gdrive']['scopes']


# ----------------------------------------------------------------------------------------------------
# Google Drive Connection
# ----------------------------------------------------------------------------------------------------

def authenticate_gdrive():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gdrive"],
        scopes=SCOPES
    )
    return creds


def establish_gdrive_connections():
    """
    Establishes a connection to Google Drive.

    Returns:
        tuple: A tuple containing the Google Drive service.
    """
    try:
        # Authenticate and create Google Drive service
        creds = authenticate_gdrive()  # Replace with your actual authentication function
        service = build('drive', 'v3', credentials=creds)
        return service

    except Exception as e:
        # Handle exceptions and provide feedback
        st.error(f"Error establishing connections: {e}")
        return None, None, None


# ----------------------------------------------------------------------------------------------------
# Database File Connection
# ----------------------------------------------------------------------------------------------------

def list_files(service):
    """Lists the files in Google Drive to help verify file IDs."""
    try:
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name, parents)").execute()
        items = results.get('files', [])
        if not items:
            st.write("No files found.")
        else:
            st.write("Files:")
            for item in items:
                st.write(f"{item['name']} ({item['id']}) {item['parents']}")
    except HttpError as error:
        st.error(f"An error occurred while listing files: {error}")


def upload_db_to_drive(service, db_name, file_id=None):
    """Uploads or updates the SQLite database file to Google Drive.

    Args:
        service: Authenticated Google Drive service instance.
        db_name: Name of the database file to upload.
        file_id: Optional; ID of the file to update. If None, a new file will be created.

    Returns:
        The ID of the uploaded or updated file.
    """
    try:
        # Define the metadata for the file (with correct MIME type for SQLite)
        file_metadata = {
            'name': db_name,
            'mimeType': 'application/x-sqlite3'  # SQLite file MIME type
        }

        # Create media file upload
        media = MediaFileUpload(db_name, mimetype='application/x-sqlite3')

        if file_id:  # If updating an existing file
            try:
                # Attempt to retrieve the file to ensure it exists
                service.files().get(fileId=file_id).execute()
                # st.write("Updating the existing file...")

                # Proceed to update the file
                file = service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()

                st.success("Data saved")
                # st.success("Database updated successfully!")
                # st.write(f"File ID: {file.get('id')}")
                # st.write(f"File metadata after update: {file}")

            except HttpError as e:
                if e.resp.status == 404:
                    st.error("File not found. Please check the file ID.")
                    return None
                else:
                    st.error(f"An error occurred: {e}")
                    return None
        else:  # If creating a new file
            # Create the file on Google Drive
            st.write("Creating a new file...")
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"Database uploaded successfully! File ID: {file.get('id')}")
            st.write(f"File metadata after creation: {file}{db_name}")

        return file.get('id')  # Return the file ID

    except HttpError as error:
        st.error(f"An error occurred during upload: {error}")
        return None


def share_file_with_user(service, file_id, user_email):
    """Shares the uploaded file with a specified user."""
    try:
        # Permission settings: granting view access to your email
        permission = {
            'type': 'user',
            'role': 'reader',  # Can change to 'reader' for read-only
            'emailAddress': user_email
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        st.success(f"File shared successfully with {user_email}")
    except HttpError as error:
        st.error(f"An error occurred while sharing the file: {error}")


def check_existing_file(service, file_name):
    """Check if a file with the given name already exists in Google Drive."""
    try:
        results = service.files().list(q=f"name='{file_name}'", fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']  # Return the ID of the first match
        return None
    except HttpError as error:
        st.error(f"An error occurred while checking for existing files: {error}")
        return None


def download_db_from_drive(service, file_id, file_name):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')  # Create a file handle for writing
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()  # Download in chunks
        # st.write(f"Download progress: {int(status.progress() * 100)}%")
        progress_bar = st.progress(0)
        st.info('Download in progress...')
        for i in range(1, 101):  # Simulate progress from 0% to 100%
            sleep(0.01)  # Simulate time taken to download
            progress_bar.progress(i / 100)  # Update the progress bar
            # st.write(f"Download progress: {i}%")  # Update the status text
    st.success(f"Data refreshed")


def delete_files_with_db_name(service, db_name):
    try:
        # Search for files with the specific database name in Google Drive
        query = f"name = '{db_name}'"
        response = service.files().list(q=query, fields="files(id, name)").execute()

        files = response.get('files', [])
        if not files:
            st.write(f"No files found with the name '{db_name}'.")
            return

        # Iterate over files and delete them
        for file in files:
            file_id = file['id']
            service.files().delete(fileId=file_id).execute()
            st.write(f"Deleted file: {file['name']} (ID: {file_id})")

    except Exception as e:
        st.error(f"An error occurred while deleting files: {e}")
