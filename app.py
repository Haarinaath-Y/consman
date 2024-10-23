import streamlit as st
from connection_utils import (download_db_from_drive, upload_db_to_drive, share_file_with_user,
                              check_existing_file, establish_gdrive_connections)
from utils import (cursor_conn, create_tables_in_db)
import Data_Entry


from authlib.integrations.requests_client import OAuth2Session

st.set_page_config(page_title="Construction Expenses Tracking App", page_icon="📚", layout="wide")
st.title("📚 Construction Expenses Tracking App")
st.sidebar.success("Navigate yourself")

# Define client ID and client secret from Google OAuth
client_id = st.secrets['gdrive']['client_id_key']
client_secret = st.secrets['gdrive']['client_secret_key']
redirect_uri = st.secrets['gdrive']['redirect_uri']  # Ensure this matches the Google Cloud Console settings

# Google OAuth 2.0 configuration
authorize_url = st.secrets['gdrive']['auth_uri']
token_url = st.secrets['gdrive']['token_uri']
userinfo_url = st.secrets['gdrive']['userinfo_uri']
scope = st.secrets['gdrive']['scope']

oauth = OAuth2Session(client_id, client_secret, redirect_uri=redirect_uri, scope=scope)


def main():
    # Establish connection with Google Drive
    service = establish_gdrive_connections()

    # Check for existing token in session state
    if "token" not in st.session_state:
        # Redirect to Google OAuth login
        authorization_url, state = oauth.create_authorization_url(authorize_url)
        st.info('Please login with Google to access the application')
        st.link_button("Login with Google", url=authorization_url)
    else:
        # Load the token
        token = st.session_state["token"]
        oauth.token = token

        # Fetch user info from Google
        response = oauth.get(userinfo_url)

        if response.status_code == 200:
            userinfo = response.json()
            user_email = userinfo.get("email")
            user_name = userinfo.get("name")
            # st.success(f"Logged in as: {user_email}")
            st.success(f"Hi {user_name}!!, 📚 Welcome to Expense Tracker App")
            if 'user_email' not in st.session_state:
                st.session_state['user_email'] = user_email
                # st.write(f'{st.session_state['user_email']}')
            # st.write(f"{userinfo}")
            # Continue to the main functionality
            setup(service)
        else:
            st.error("Failed to recognize the user 😥!!")
            # st.error("Failed to fetch user information. Status Code: " + str(response.status_code))

    # Handle the authorization code if present
    code = st.query_params.get("code")
    if code and "token" not in st.session_state:
        try:
            # Fetch the token using the code
            token = oauth.fetch_token(token_url, code=code, grant_type="authorization_code")
            st.session_state["token"] = token
            st.success("Authentication completed successfully.")
            st.rerun()  # Refresh the app to show user info
        except Exception as e:
            st.error(f"An error occurred during authentication")
            st.info('Please try login again')
            print(f'Error log: {e}')


def database_setup(service):
    # Check if the database has been downloaded already
    conn, cursor, db_name = cursor_conn()
    # st.write(db_name)
    if 'db_downloaded' not in st.session_state:
        st.session_state.db_downloaded = False  # Initialize the session state variable

    # Check if the database has been downloaded already
    if 'db_created' not in st.session_state:
        st.session_state.db_created = False  # Initialize the session state variable

    existing_file_id = check_existing_file(service, db_name)
    if existing_file_id:
        if not st.session_state.db_downloaded:  # Download the DB only if not done yet
            download_db_from_drive(service, existing_file_id, db_name)
            st.session_state.db_downloaded = True
            print(f"Updated existing file with ID: {existing_file_id}, File Name: {db_name}")
        # st.write(f"File ID: {existing_file_id}")
    else:
        if not st.session_state.db_created:  # Create the DB file
            # st.write('No file ID')
            create_tables_in_db(db_name)
            result_id = upload_db_to_drive(service, db_name, None)
            st.write(f"Created new file with name: {db_name}")
            share_file_with_user(service, result_id, st.session_state['user_email'])
            st.info('Please check your google drive in Shared With Me folder !!')
            st.session_state.db_created = True

    # Log to track which state the function is in
    if st.session_state['db_downloaded']:
        st.write("DB has already been downloaded this session.")
    if st.session_state['db_created']:
        st.write("DB has already been created this session.")

    # Store service and db_name in session state for later use
    st.session_state.service = service
    st.session_state.db_name = db_name

    st.session_state.page = "show_main_functionality"
    st.rerun()


def setup(service):
    # Check which page to show based on the session state
    if 'page' not in st.session_state:
        st.session_state.page = "database_setup"

    # Check which page to show based on the session state
    if st.session_state.page == "show_main_functionality":
        # Pass service and db_name
        Data_Entry.show_main_functionality(st.session_state.service, st.session_state.db_name)
    else:
        database_setup(service)  # Show the main page (database setup)


if __name__ == "__main__":
    main()
