import streamlit as st
from connection_utils import (upload_db_to_drive, share_file_with_user, check_existing_file)
from utils import (fetch_data_from_db, register_date_adapter_converter, create_new_project, store_session_state,
                   clear_input, connect_db)
from pandas import DataFrame
import datetime


def show_main_functionality(service, db_name):
    # Your existing functionality for handling database operations, file uploads, etc.
    # st.info("Entering main functionality...")
    # Checking if there are any projects

    if 'db_downloaded' in st.session_state and st.session_state.db_downloaded:
        project_query = "SELECT project_id || ' - ' || project_name AS project FROM projects;"
        project = fetch_data_from_db(project_query, db_name)
        # st.write(project)
        project_decision = st.selectbox('Select an option', ["Select Existing Project", "Create New Project"])

        # Entering into function if there are projects
        if project and project_decision == 'Select Existing Project':
            project_with_blank = ["Project Names with Project ID"] + project
            project_selection = st.selectbox("Select the project:", project_with_blank)
            project_id_selected = project_selection.split(' - ')[0]

            if project_selection != "Project Names with Project ID":
                st.success(f"You have selected the project: **{project_selection}**")
                st.session_state['project_id_selected'] = project_id_selected
                project_id = st.session_state['project_id_selected']

                store_session_state("project_id_selected", project_id_selected)
                store_session_state("project_selection", project_selection)

                categories = fetch_data_from_db('SELECT category FROM category', db_name)
                payment_options = fetch_data_from_db('SELECT mode_of_payment FROM mode_of_payment', db_name)
                stage_options = fetch_data_from_db('SELECT stage FROM stages', db_name)
                existing_vendors = fetch_data_from_db('SELECT distinct vendor FROM purchases', db_name)
                vendor_option = st.selectbox("Vendor Type:", ["Select Existing Vendor", "Enter New Vendor"],
                                             on_change=lambda: clear_input('vendor'))
                mode_of_payment = st.selectbox("Select mode of payment:", payment_options,
                                               index=payment_options.index(st.session_state.get("reset_mode_of_payment", payment_options[0])),
                                               on_change=lambda: clear_input('paid_amount'), key="mode_of_payment",
                                               placeholder="Select Mode of Payment")

                # Form for user data input
                with st.form("purchases_data_entry", clear_on_submit=True):
                    st.header("🧾 Purchase Data Entry Form")
                    # Create two columns
                    col1, col2, col3 = st.columns(3)

                    # First column: Item name input
                    with col1:
                        item_name = st.text_input("Enter the item name:", placeholder='Please enter an item name',
                                                  key='item_name')

                    # Second column: Item quantity input
                    with col2:
                        unit = st.selectbox("Select unit:", ["Nos", "MT", "Liters", "Units", "Kg", "Others"], key='unit', index=None,
                                            placeholder='Please choose a unit if applicable')

                    # Second column: Select box for units or item type
                    with col3:
                        item_qty = st.number_input("Enter the item quantity:", min_value=0.0, max_value=1000000.0,
                                                   step=0.01, key='item_qty', value=None,
                                                   placeholder='Please enter an item quantity')

                    col4, col5 = st.columns(2)

                    with col4:
                        stage = st.selectbox("Select stage:", stage_options, key='stage', index=None,
                                             placeholder='Please select a stage')

                    with col5:
                        category = st.selectbox("Select category:", categories, key='category', index=None,
                                                placeholder='Please select a category')

                    # Conditional input based on vendor option
                    if vendor_option == "Select Existing Vendor":
                        vendor = st.selectbox("Select vendor:", existing_vendors, key="vendor", index=None,
                                              placeholder='Please choose a vendor')
                    elif vendor_option == "Enter New Vendor":
                        vendor = st.text_input("Enter the new vendor name:", key="vendor",
                                               placeholder='Please enter an vendor name')
                    register_date_adapter_converter()
                    date = st.date_input("Select the date:", datetime.date.today(), min_value=datetime.date(2000, 1, 1),
                                         max_value=datetime.date.today(), key='date')
                    purchase_amount = st.number_input("Enter the purchase amount:", min_value=-10000, max_value=1000000,
                                                      value=0, key='purchase_amount')

                    # Conditionally display the paid amount input
                    if mode_of_payment != "No Payment":
                        paid_amount = st.number_input("Enter the paid amount:", min_value=0, max_value=1000000, value=0,
                                                      key="paid_amount")
                        paid_by = st.text_input("Who paid the amount?:", key='paid_by')
                    else:
                        paid_amount = 0  # Default to 0 if 'No Payment' is selected
                        paid_by = None

                    notes = st.text_input("Add notes if necessary:", key='notes')

                    required_fields = [item_name, vendor, mode_of_payment, category, stage, date]
                    submit_enabled = all(required_fields) and (purchase_amount != 0 or paid_amount > 0)

                    submitted = st.form_submit_button("Submit", icon="🚨")

                if submitted:
                    if submit_enabled:
                        with connect_db(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''INSERT INTO purchases 
                                            (project_id, item_name, item_qty, unit, vendor, stage, category, date, 
                                            purchase_amount, mode_of_payment, paid_amount, paid_by, notes)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                           (project_id, item_name, item_qty, unit, vendor, stage, category, date,
                                            purchase_amount, mode_of_payment, paid_amount, paid_by, notes))
                            conn.commit()
                            st.success("Data submitted successfully!")
                    else:
                        st.error("All fields are mandatory! Please fill in all fields.")

                if st.button("View Purchases"):
                    with connect_db(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute(f'''
                            SELECT 
                                purchase_id as 'Purchase ID', 
                                item_name as 'Item Name',
                                unit as 'Unit', 
                                item_qty as 'Item Qty',                        
                                CASE 
                                WHEN unit = 'Nos' or unit = 'Others' OR unit is null
                                THEN COALESCE(CAST(item_qty AS INTEGER),'') || ' ' || COALESCE(unit,'')
                                ELSE COALESCE(printf('%.2f', item_qty), '') || ' ' || COALESCE(unit,'')
                            END AS 'Item Quantity',
                            vendor as Vendor, 
                            stage as Stage, 
                            category as Category,
                            date as Date, 
                            purchase_amount as 'Purchase Amount', 
                            mode_of_payment as 'Mode of Payment',
                            paid_amount as 'Paid Amount',
                            paid_by as 'Paid By',
                            notes as Notes
                            FROM purchases
                            WHERE project_id = {project_id}    
                    ''')
                    data = cursor.fetchall()
                    if data:
                        results_df = DataFrame(data, columns=[desc[0] for desc in cursor.description])
                        st.dataframe(results_df)
                    else:
                        st.write("No data found for the selected criteria.")

                if st.button("Save"):
                    existing_file_id = check_existing_file(service, db_name)
                    if existing_file_id:
                        result_id = upload_db_to_drive(service, db_name, existing_file_id)
                        st.success(f"Updated the file with ID: {db_name}")
                        share_file_with_user(service, result_id, st.session_state['user_email'])
                        st.rerun()
                    else:
                        st.write('Error while saving the file')

        else:
            create_new_project(db_name)


if __name__ == "__main__":
    show_main_functionality(None, None)
