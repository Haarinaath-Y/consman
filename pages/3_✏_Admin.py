import streamlit as st
from utils import delete_the_last_project, edit_project, delete_purchase_record, cursor_conn

st.set_page_config(
    page_title='Admin',
    layout="wide"
)


def main():
    st.header("Edit/Delete data")
    try:
        conn, cursor, db_name = cursor_conn()
        try:
            if st.session_state["token"]:
                st.subheader("Edit Project Details", divider=True)
                edit_project(db_name)
                st.subheader("Delete the Last Project", divider=True)
                delete_the_last_project(db_name)
            try:
                if st.session_state['project_id_selected']:
                    st.subheader("Delete the Unwanted Purchase Entry", divider=True)
                    delete_purchase_record(db_name)
            except Exception as e:
                st.warning(f"Please select the project in Home Page !!")
                print(f'Error log: {e}')
        except Exception as e:
            st.warning(f"Please login with Google in Home Page!!")
            print(f'Error log: {e}')
    except Exception as e:
        st.warning(f"Please login with Google in Home Page!!")
        print(f'Error log: {e}')


if __name__ == "__main__":
    main()
