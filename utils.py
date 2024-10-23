import sqlite3
import streamlit as st
import os
from datetime import datetime
import pandas as pd
from time import sleep
import datetime


def db_name_creation():
    try:
        if 'user_email' in st.session_state and st.session_state['user_email']:
            user_email = st.session_state['user_email'].split('@')[0]
            database_name = f'{user_email}.db'
            return database_name
        else:
            st.error('Unable to identify the user !!')
    except Exception as e:
        st.error(f'Error while creating db file {e}')


def connect_db(database_name):
    return sqlite3.connect(database_name)


def db_cursor(database_name):
    # Try connecting to the database and executing the query
    connection = connect_db(database_name)
    conn_cursor = connection.cursor()
    return connection, conn_cursor


def cursor_conn():
    database_name = db_name_creation()
    connection, cursor = db_cursor(database_name)
    return connection, cursor, database_name


# ----------------------------------------------------------------------------------------------------
# Table Creation
# ----------------------------------------------------------------------------------------------------

def create_tables_in_db(database_name):
    """
    Creates necessary tables in the database.
    """

    stages_to_insert = [
        ('STAGE-1', 'Basement'),
        ('STAGE-2', 'Roof'),
        ('STAGE-3', 'Masonry'),
        ('STAGE-4', 'Finishes'),
        ('STAGE-5', 'Site Work and Fixtures')
    ]

    categories_to_insert = [
        "General",
        "Material",
        "MEP Labour",
        "Mason Labour",
        "Misc Civil Labour",
        "Paint Labour",
        "Tiling Labour",
        "Joinery"
    ]

    modes_of_payment_to_insert = [
        "No Payment",
        "UPI",
        "Credit Card",
        "Debit Card",
        "Cash",
        "Bank Transfer"
    ]

    try:
        with connect_db(database_name) as conn:
            cursor = conn.cursor()
            # Example table creation queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "projects" (
                    "project_id"	INTEGER,
                    "project_name"	TEXT NOT NULL,
                    "project_location"	TEXT,
                    PRIMARY KEY("project_id" AUTOINCREMENT)
                );     
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "purchases" (
                    "purchase_id"	INTEGER,
                    "project_id"	INTEGER NOT NULL,
                    "item_name"	TEXT NOT NULL,
                    "item_qty"	REAL,
                    "unit"	TEXT,
                    "vendor"	TEXT NOT NULL,
                    "stage"	TEXT NOT NULL,
                    "category"	TEXT NOT NULL,
                    "date"	TEXT NOT NULL,
                    "purchase_amount"	REAL NOT NULL,
                    "mode_of_payment"	TEXT NOT NULL,
                    "paid_amount"	REAL,
                    "paid_by"	TEXT,
                    "notes"	TEXT,
                    PRIMARY KEY("purchase_id" AUTOINCREMENT),
                    CONSTRAINT "project_fk" FOREIGN KEY("project_id") REFERENCES "projects"("project_id")
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "stages" (
                    "stage_id"	TEXT NOT NULL,
                    "stage"	TEXT NOT NULL
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "category" (
                    "category"	TEXT
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "mode_of_payment" (
                    "mode_of_payment"	TEXT
                );
            ''')

            for stage_id, stage_name in stages_to_insert:
                cursor.execute('''
                    INSERT INTO stages (stage_id, stage)
                    SELECT ?, ?
                    WHERE NOT EXISTS (SELECT 1 FROM stages WHERE stage_id = ? OR stage = ?)
                ''', (stage_id, stage_name, stage_id, stage_name))

            for category in categories_to_insert:
                cursor.execute('''
                    INSERT INTO category (category)
                    SELECT ?
                    WHERE NOT EXISTS (SELECT 1 FROM category WHERE category = ?)
                ''', (category, category))

            for mode_of_payment in modes_of_payment_to_insert:
                cursor.execute('''
                    INSERT INTO mode_of_payment (mode_of_payment)
                    SELECT ?
                    WHERE NOT EXISTS (SELECT 1 FROM mode_of_payment WHERE mode_of_payment = ?)
                ''', (mode_of_payment, mode_of_payment))

            # Connection commit and close
            st.success("Tables created successfully!")
            conn.commit()

    except Exception as e:
        st.error(f"Error creating tables: {e}")


# ----------------------------------------------------------------------------------------------------
# Project Creation or deletion
# ----------------------------------------------------------------------------------------------------

def create_new_project(database_name):
    """Creates a new project in the database."""
    with st.form('Create New Project'):
        project_name = st.text_input('Enter the project name:')
        project_location = st.text_input('Enter the project location:')
        project_submission = st.form_submit_button('Create')

    if project_submission:
        if project_name:  # Check if the project name is provided
            with connect_db(database_name) as conn:
                # Insert the new project into the database
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO projects 
                                  (project_name, project_location)
                                  VALUES (?, ?)''',
                               (project_name, project_location))
                conn.commit()  # Commit the changes
                st.success("New project created successfully!")
        else:
            st.error('Please enter the project name')


def delete_the_last_project(database_name):
    with st.form('Delete a Project'):
        project_query = "SELECT project_id || ' - ' || project_name AS project FROM projects;"
        project = fetch_data_from_db(project_query, database_name)
        project_id_selection = st.selectbox('Select a project to delete:', project)
        project_submission = st.form_submit_button('Delete')
        project_id_selected = project_id_selection.split(' - ')[0]

    if project_submission:
        try:
            if project_id_selection:
                with connect_db(database_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"""select max(project_id) from projects 
                                        where project_id not in ({project_id_selected})""")
                    b = cursor.fetchone()[0]
                    cursor.execute(f"UPDATE sqlite_sequence SET seq = {b} WHERE name = 'projects';")
                    cursor.execute(f'''DELETE FROM projects WHERE project_id = {project_id_selected}''')
                    conn.commit()
                    st.success("Project deleted successfully!")
            else:
                st.error('Select a valid project id')
        except Exception as e:
            st.error(f'Error {e}')


def edit_project(database_name):
    with connect_db(database_name) as conn:
        cursor = conn.cursor()
        # Fetch the list of projects
        cursor.execute("SELECT project_id, project_name || ' - ' || project_location AS project_info FROM projects")
        projects = cursor.fetchall()

        if projects:
            # Convert fetched projects into a dictionary for easier selection
            project_dict = {f"{p[1]}": p[0] for p in projects}

            # Allow the user to select a project
            selected_project = st.selectbox("Select the project to edit:", list(project_dict.keys()))
            selected_project_id = project_dict[selected_project]

            # Fetch the current project details
            cursor.execute("SELECT project_name, project_location FROM projects WHERE project_id = ?",
                           (selected_project_id,))
            project_details = cursor.fetchone()

            # Prepopulate the current project details in input fields
            new_project_name = st.text_input("Edit Project Name:", value=project_details[0])
            new_project_location = st.text_input("Edit Project Location:", value=project_details[1])

            if st.button("Save Changes"):
                # Update the project details in the database
                cursor.execute("""
                    UPDATE projects 
                    SET project_name = ?, project_location = ? 
                    WHERE project_id = ?
                """, (new_project_name, new_project_location, selected_project_id))
                conn.commit()
                # Set a flag in session_state before rerunning
                st.session_state['project_updated'] = True
                st.rerun()

            # Check for the success flag in session_state
            if 'project_updated' in st.session_state and st.session_state['project_updated']:
                st.success("Project details updated successfully!")
                # Reset the flag to prevent showing success again on the next rerun
                st.session_state['project_updated'] = False
        else:
            st.warning("No projects found.")


# ----------------------------------------------------------------------------------------------------
# Fetching data and displaying data from Database
# ----------------------------------------------------------------------------------------------------


def fetch_data_from_db(query, database_name):
    try:
        with connect_db(database_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            data = [row[0] for row in cursor.fetchall()]
            return data

    except sqlite3.DatabaseError as e:
        # Catch database-related errors
        st.info(f"Try refresh button above {e}")
        return None

    except Exception as e:
        # Catch any other exceptions
        st.error(f"Try refresh button above {e}")
        return None


def fetch_and_display_data(query, database_name):
    """
    Execute the given SQL query, fetch the results, and display them in a Streamlit app.
    Handles any SQL syntax errors and displays appropriate messages.

    Args:
        query (str): The SQL query to be executed.
        :param query: SQL query
        :param database_name: db file name
    """
    try:
        with connect_db(database_name) as conn:
            cursor = conn.cursor()
            # Execute the SQL query
            cursor.execute(query)

            # Fetch all rows from the executed query
            results = cursor.fetchall()

            # Check if there are any results
            if results:
                # Convert rows to a pandas DataFrame for better display
                results_df = pd.DataFrame(results, columns=[desc[0] for desc in cursor.description])
                # Check if 'Purchase Amount' column exists and apply formatting
                for col in ['Purchase Amount', 'Paid Amount', 'Difference']:
                    if col in results_df.columns:
                        results_df[col] = results_df[col].apply(format_currency)

                # Display the DataFrame in tabular format
                st.dataframe(results_df)  # You can also use st.table(df) for a static table
            else:
                # Inform the user if no data was found
                st.warning("No data found for the selected criteria.")

    except sqlite3.OperationalError:
        # Catch and handle specific MySQL errors
        st.warning("Please check if you've selected a valid project")

    except Exception as e:
        # Catch any other exceptions
        st.error(f"An unexpected error occurred: {e}")


# ----------------------------------------------------------------------------------------------------
# Handling session state
# ----------------------------------------------------------------------------------------------------


# Function to store the selected value in session state
def store_session_state(key, value):
    if key == 'project_selection' and value == "Project Names with Project ID" or value == 'Null' or value == '':
        st.warning("Please select a valid project")
    else:
        st.session_state[key] = value


# Function to clear vendor input when switching options
def clear_input(key):
    if key in st.session_state:
        del st.session_state[key]


def display_loading_message(text, duration=1, element_type='text'):
    """Updates a placeholder with the specified Streamlit element for a specified duration.

    Args:
        text (str): The text to display in the placeholder.
        duration (int): How long to display the element (in seconds).
        element_type (str): The type of element to display ('text', 'markdown', 'header', etc.).
    """
    # Create a placeholder
    placeholder = st.empty()

    # Display the specified Streamlit element in the placeholder
    with placeholder:
        if element_type == 'text':
            st.write(text)
        elif element_type == 'markdown':
            st.markdown(text)
        elif element_type == 'header':
            st.header(text)
        elif element_type == 'subheader':
            st.subheader(text)
        elif element_type == 'error':
            st.error(text)
        elif element_type == 'success':
            st.success(text)
        elif element_type == 'warning':
            st.warning(text)
        elif element_type == 'info':
            st.info(text)
        else:
            st.write("Invalid element type specified.")

        sleep(duration)  # Simulating a delay for the duration specified

    # Clear the placeholder
    placeholder.empty()


def register_date_adapter_converter():
    """Register SQLite adapters and converters for datetime.date objects."""

    # Define the adapter to convert datetime.date to string
    def adapt_date(date_obj):
        """Convert datetime.date to string for SQLite."""
        return date_obj.strftime("%Y-%m-%d")

    # Define the converter to convert string back to datetime.date
    def convert_date(date_str):
        """Convert string back to datetime.date."""
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    # Register the adapter and converter for SQLite
    sqlite3.register_adapter(datetime.date, adapt_date)
    sqlite3.register_converter("DATE", convert_date)


# ----------------------------------------------------------------------------------------------------
# Formatting data values
# ----------------------------------------------------------------------------------------------------

# Display all purchases data for each
def to_title_case(column_values):
    return [str(value).title().replace("_", " ") for value in column_values]


# Display all purchases data for each
def to_lower_case(column_values):
    return str(column_values).lower()


def format_currency(value):
    """Format value as Indian Rupees with commas."""
    if isinstance(value, (int, float)):
        return f"₹{value:,.2f}"
    return value


def format_percentage(value):
    """Format value as a percentage."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"
    return value


# ----------------------------------------------------------------------------------------------------
# Local file and GDrive file modified time
# ----------------------------------------------------------------------------------------------------


def get_google_drive_modified_time(service, file_id):
    """Fetches the last modified time of a file in Google Drive."""
    file = service.files().get(fileId=file_id, fields='modifiedTime').execute()
    modified_time = file['modifiedTime']

    # Parse the modified time and convert it to a datetime object
    gdrive_modified_time = datetime.strptime(modified_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    return gdrive_modified_time


def get_local_file_modified_time(file_path):
    """Fetches the last modified time of a local file."""
    if os.path.exists(file_path):
        last_modified_time = os.path.getmtime(file_path)
        return datetime.fromtimestamp(last_modified_time)  # Return as UTC
    else:
        return None  # If the file does not exist


def list_files_in_directory(directory):
    """Lists file names, their IDs (if applicable), and last modified datetime in the specified directory."""
    # Initialize a list to hold the file information
    file_info = []

    # Iterate through the files in the specified directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if it's a file
        if os.path.isfile(file_path):
            # Get the last modified time
            last_modified_time = os.path.getmtime(file_path)
            last_modified_datetime = datetime.fromtimestamp(last_modified_time)

            # Optionally, you can generate a unique file ID (e.g., using the file's path hash)
            file_id = hash(file_path)  # Simple hash as a unique identifier

            # Append the file info as a dictionary
            file_info.append({
                'file_name': filename,
                'file_id': file_id,
                'last_modified': last_modified_datetime.strftime('%Y-%m-%d %H:%M:%S')
            })

    return file_info


# ----------------------------------------------------------------------------------------------------
# Overall Expenses report
# ----------------------------------------------------------------------------------------------------

def expenses_pivot(database_name):
    try:
        with connect_db(database_name) as conn:
            cursor = conn.cursor()
            # Fetch distinct categories from the category table
            cursor.execute("SELECT category FROM category")
            categories = cursor.fetchall()

            # Check if categories exist
            if not categories:
                st.error("No categories found.")
                return

            # Start building the SQL query for each stage and category
            sql_query = "SELECT stage as Stage"

            # Add dynamic category columns to the SQL query
            for (category,) in categories:
                sql_query += f", COALESCE(SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END), 0) AS '{category}'"

            # Add grand total column for each stage
            sql_query += ", COALESCE(SUM(p.purchase_amount), 0) AS 'Purchase Amount'"

            # Complete the main SQL query
            sql_query += " FROM purchases p GROUP BY stage"

            # Start building the UNION query for totals
            union_query = " UNION ALL SELECT 'Total'"

            # Add totals for each category
            for (category,) in categories:
                union_query += f", COALESCE(SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END), 0)"

            # Add grand total
            union_query += ", COALESCE(SUM(p.purchase_amount), 0) FROM purchases p"

            # Add the row for percentage
            percentage_query = " UNION ALL SELECT 'Percentage'"

            # First, fetch the grand total to use for percentage calculation
            cursor.execute("SELECT COALESCE(SUM(purchase_amount), 0) FROM purchases")
            grand_total = cursor.fetchone()[0]

            # Check if grand total is fetched
            if grand_total is None:
                st.error("Failed to fetch grand total.")
                return

            # Calculate percentage for each category and grand total
            for (category,) in categories:
                percentage_query += f", CASE WHEN {grand_total} > 0 THEN ROUND(100 * SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END) / {grand_total}, 2) ELSE 0 END"

            # Grand total percentage (which will always be 100%)
            percentage_query += f", CASE WHEN {grand_total} > 0 THEN 100 ELSE 0 END FROM purchases p"

            # Combine the main query, totals, and percentage rows
            final_query = sql_query + union_query + percentage_query

            # Display the final query for debugging
            # st.write("Executing SQL Query:")
            # st.code(final_query)

            # Execute the dynamic SQL query
            cursor.execute(final_query)

            results = cursor.fetchall()

            # Get column names
            column_names = [desc[0] for desc in cursor.description]

            # Check if results were fetched
            if not results:
                st.error("No results found for the query.")
                return

            # Convert the results into a pandas DataFrame
            df = pd.DataFrame(results, columns=column_names)

            # Ensure numeric columns are correctly typed
            for col in df.columns[1:]:  # All columns except 'stage'
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Create a copy for formatted display
            formatted_df = df.copy()

            # Format all numeric columns (except 'stage') as currency
            for col in formatted_df.columns[1:-1]:  # All category columns (excluding Grand_Total)
                formatted_df[col] = formatted_df[col].apply(format_currency)

            grand_total_col = formatted_df.columns[-1]  # Get the last column name (Grand_Total)

            # Change the dtype of the 'Grand_Total' column to 'object' to avoid dtype incompatibility warning
            formatted_df[grand_total_col] = formatted_df[grand_total_col].astype('object')

            for i in range(len(formatted_df) - 1):  # Loop through all rows except the last one
                formatted_df.at[i, grand_total_col] = format_currency(df.at[i, grand_total_col])

            # Format the last row (percentage row) correctly
            last_row_index = formatted_df.index[-1]  # Index of the percentage row
            for col in formatted_df.columns[1:]:  # All columns except 'stage'
                if col != 'Stage':
                    raw_value = df.at[last_row_index, col]  # Get the raw numeric value
                    formatted_df.at[last_row_index, col] = format_percentage(raw_value)  # Format for display

            # Highlight Total and Percentage rows
            def highlight_rows(row):
                if row['Stage'] == 'Total':
                    return ['background-color: #FF4B4B'] * len(row)
                elif row['Stage'] == 'Percentage':
                    return ['background-color: #4B0082'] * len(row)
                else:
                    return [''] * len(row)

            # Apply highlighting
            styled_df = formatted_df.style.apply(highlight_rows, axis=1)

            # Display the styled DataFrame in Streamlit
            st.dataframe(styled_df, use_container_width=True)

    except sqlite3.Error as err:
        st.error(f"Database Error: {err}")


def purchase_amounts(database_name):
    try:
        with connect_db(database_name) as conn:
            cursor = conn.cursor()
            # Fetch distinct categories from the category table
            cursor.execute("SELECT category FROM category")
            categories = cursor.fetchall()

            # Fetch distinct stages from the stages table
            cursor.execute("SELECT stage FROM stages")
            stages = cursor.fetchall()

            # Check if categories or stages exist
            if not categories or not stages:
                st.error("No categories or stages found.")
                return

            # Create a list of stages and categories
            stages_list = [stage[0] for stage in stages]
            categories_list = [category[0] for category in categories]

            # Build SQL query to get purchase amounts per category and stage
            sql_query = "SELECT p.category as Category"

            # Add dynamic stage columns
            for stage in stages_list:
                sql_query += f", COALESCE(SUM(CASE WHEN p.stage = '{stage}' THEN p.purchase_amount ELSE 0 END), 0) AS '{stage}'"

            # Add grand total for each category
            sql_query += ", COALESCE(SUM(p.purchase_amount), 0) AS 'Total'"

            # Complete the SQL query
            sql_query += " FROM purchases p GROUP BY p.category"

            # Execute the main SQL query
            cursor.execute(sql_query)
            results = cursor.fetchall()

            # Convert the results into a pandas DataFrame
            column_names = ['Category'] + stages_list + ['Total']
            df = pd.DataFrame(results, columns=column_names)

            # Ensure all categories are included, even if they have no purchases
            all_categories_df = pd.DataFrame(categories_list, columns=['Category'])
            df = pd.merge(all_categories_df, df, on='Category', how='left').fillna(0)

            # Calculate the grand total for each stage (column total)
            grand_total_row = df.sum(numeric_only=True).to_frame().T
            grand_total_row.insert(0, 'Category', 'Grand Total')

            # Append the grand total row to the DataFrame
            df = pd.concat([df, grand_total_row], ignore_index=True)

            # Calculate percentage for each category based on the grand total
            grand_total = grand_total_row['Total'].iloc[0]

            if grand_total > 0:
                df['Percentage'] = (df['Total'] / grand_total * 100).round(2)
            else:
                df['Percentage'] = 0

            # Calculate the percentage for each stage (column percentage)
            percentage_row = pd.DataFrame(columns=df.columns)
            percentage_row.loc[0] = ['Percentage'] + [
                (df[stage].iloc[:-1].sum() / grand_total * 100).round(2) if grand_total > 0 else 0
                for stage in stages_list
            ] + [100, '']

            # Append the percentage row to the DataFrame
            df = pd.concat([df, percentage_row], ignore_index=True)

            # Ensure numeric columns are correctly typed
            for col in df.columns[1:]:  # All columns except 'Category'
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Create a copy for formatted display
            formatted_df = df.copy()

            # Format all numeric columns (except 'Category') as currency
            for col in formatted_df.columns[1:-2]:  # All columns except 'Category', 'Total', and 'Percentage'
                formatted_df[col] = formatted_df[col].apply(format_currency)

            # Format Total column
            formatted_df['Total'] = formatted_df['Total'].apply(format_currency)

            # Format Percentage column (ensure no currency formatting)
            formatted_df['Percentage'] = formatted_df['Percentage'].apply(format_percentage)

            grand_total_col = formatted_df.columns[-2]
            # Change the dtype of the 'Grand_Total' column to 'object' to avoid dtype incompatibility warning
            formatted_df[grand_total_col] = formatted_df[grand_total_col].astype('object')

            for i in range(len(formatted_df) - 1):  # Loop through all rows except the last one
                formatted_df.at[i, grand_total_col] = format_currency(df.at[i, grand_total_col])

            # Format the last row (percentage row) correctly
            last_row_index = formatted_df.index[-1]  # Index of the percentage row
            for col in formatted_df.columns[1:]:  # All columns except 'stage'
                if col != 'Stage':
                    raw_value = df.at[last_row_index, col]  # Get the raw numeric value
                    formatted_df.at[last_row_index, col] = format_percentage(raw_value)

            def highlight_rows(row):
                styles = [''] * len(row)

                # Highlight entire row for Grand Total
                if row['Category'] == 'Grand Total':
                    styles = ['background-color: #93c47d'] * len(row)  # Gold for Grand Total
                # Highlight entire row for Percentage
                elif row['Category'] == 'Percentage':
                    styles = ['background-color: #FF4B4B'] * len(row)  # Indigo for Percentage

                return styles

            def highlight_last_column(s):
                # Create a default style
                styles = pd.DataFrame('', index=s.index, columns=s.columns)

                styles.iloc[:, -1] = ['background-color: #FF4B4B']
                styles.iloc[:, -2] = ['background-color: #93c47d']
                return styles

            # Function to highlight the last value of the second-to-last column
            def highlight_last_value(s):
                # Create a default style DataFrame with empty strings
                styles = pd.DataFrame('', index=s.index, columns=s.columns)

                # Get the index of the last row
                last_index_in_df = s.index[-1]

                # Apply color to the last value of the second-to-last column
                styles.iloc[last_index_in_df, -2] = 'background-color: #FF4B4B'  # Change color (Tomato)

                return styles

            # Apply row highlighting
            styled_df = formatted_df.style.apply(highlight_rows, axis=1)
            styled_df = styled_df.apply(highlight_last_column, axis=None)
            styled_df = styled_df.apply(highlight_last_value, axis=None)

            # Display the styled DataFrame in Streamlit
            st.dataframe(styled_df, use_container_width=True)

    except sqlite3.Error as err:
        st.error(f"Database Error: {err}")


# ----------------------------------------------------------------------------------------------------
# Delete Record Function
# ----------------------------------------------------------------------------------------------------

def delete_purchase_record(database_name):
    # Fetch existing purchase IDs for deletion
    purchases_query = "SELECT purchase_id FROM purchases"
    purchases = fetch_data_from_db(purchases_query, database_name)

    # Convert list of tuples to a list of IDs for the select box
    purchases_with_blank = ["Select Purchase ID to delete"] + purchases  # Flatten the list of tuples

    with st.form("delete_form"):
        purchase_id = st.selectbox("Select Purchase ID", purchases_with_blank)
        submitted = st.form_submit_button("Delete")

        if submitted and purchase_id != "Select Purchase ID to delete":
            # Set the purchase ID in session state for confirmation
            st.session_state.purchase_id_to_delete = purchase_id
            st.session_state.confirm_delete = True

    # Confirmation message and action
    if st.session_state.get("confirm_delete", False):
        st.warning(f"Are you sure you want to delete Purchase ID: {st.session_state.purchase_id_to_delete}?", icon="⚠️")
        fetch_and_display_data(f'select * from purchases where purchase_id = {st.session_state.purchase_id_to_delete}', database_name)

        # Buttons for confirmation
        if st.button("Yes, delete"):
            try:
                with connect_db(database_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM purchases WHERE purchase_id = ?", (st.session_state.purchase_id_to_delete,))
                    conn.commit()
                    st.success(f"Purchase ID {st.session_state.purchase_id_to_delete} deleted successfully.")
                    # Reset the session state
                    st.session_state.confirm_delete = False
            except sqlite3.Error as e:
                st.error(f"An error occurred while deleting: {e}")

        if st.button("No, cancel"):
            st.info("Deletion canceled.")
            # Reset the session state
            st.session_state.confirm_delete = False

        # Reset the form if needed after the operation
        if not st.session_state.get("confirm_delete", False):
            st.rerun()
