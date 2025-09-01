import streamlit as st
import io
import os
from data_tool import clean_from_tags, enrich_from_master

st.set_page_config(layout="wide", page_title="Capsule CSV Data Utility")

st.title("Capsule CSV Data Utility")
st.write("A tool to help clean and enrich CSV exports from Capsule CRM.")

# --- Sidebar for Mode Selection ---
st.sidebar.header("Select Operation Mode")
mode = st.sidebar.radio(
    "Choose your task:",
    ("Clean from Tags", "Enrich from Master"),
    help="""
    - **Clean from Tags**: Updates 'Sector' and 'Category' in a single file based on its 'Tags' column.
    - **Enrich from Master**: Updates a target file (e.g., people) using a master file (e.g., organisations).
    """
)

# --- Main App Body ---

if mode == "Clean from Tags":
    st.header("Mode: Clean a File Using its 'Tags' Column")
    st.markdown("""
    This mode processes a single CSV file. For each row, it inspects the `Tags` column.
    If the `Sector` or `Category` fields are empty, it populates them based on predefined mappings in the script.
    """)
    
    with st.expander("View File Requirements & Troubleshooting"):
        st.markdown("""
        **Input File Requirements:**
        - Must be a valid CSV file.
        - Must contain a column named `Tags`. The values in this column (e.g., `construction`, `Software & Technology`) are used to determine the correct `Sector` and `Category`.
        - The `Sector` and `Category` columns are optional. If they don't exist, they will be created in the output file.

        **Troubleshooting Tips:**
        - **"No rows were updated" message:**
            - Check if the `Tags` column in your source file contains values that match the mappings defined in the script.
            - Verify that the `Sector` and `Category` fields you expect to be updated are actually empty. The script is designed not to overwrite existing correct values.
        - **Error during processing:**
            - Ensure your file is a standard CSV format (e.g., saved as "CSV UTF-8" from Excel) and is not corrupted.
        """)

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload the CSV file to clean", type="csv")
    
    if uploaded_file is not None:
        if st.button("Process File", type="primary"):
            with st.spinner("Cleaning file... This may take a moment."):
                # Streamlit's UploadedFile is a file-like object. We decode it to a text stream.
                string_io = io.StringIO(uploaded_file.getvalue().decode("utf-8-sig"))
                
                output_csv, updated, total = clean_from_tags(string_io)
                
                st.success(f"**Processing complete!** {updated} out of {total} rows were updated.")
                
                # Get original filename without extension
                file_base, _ = os.path.splitext(uploaded_file.name)

                st.download_button(
                    label="⬇️ Download Cleaned File",
                    data=output_csv,
                    file_name=f"{file_base}_cleaned.csv",
                    mime="text/csv",
                )

elif mode == "Enrich from Master":
    st.header("Mode: Enrich a Target File Using a Master File")
    st.markdown("""
    This mode uses a **master file** (e.g., an organisation list) to enrich a **target file** (e.g., a people list).
    It matches organisations between the two files and copies the `Sector` and `Category` from the master to the target where they are missing.
    """)
    
    with st.expander("View File Requirements & Troubleshooting"):
        st.markdown("""
        **File Requirements:**

        **1. Master File:**
        - This should be your clean reference list (e.g., a correct list of organisations).
        - Must contain a column with the organisation's name. The script looks for a column named `Name` first, then falls back to `Organisation`.
        - Must contain the `Sector` and `Category` columns with the correct data you want to copy *from*.

        **2. Target File (The File to Update):**
        - This is the file you want to enrich (e.g., a list of people).
        - Must contain an `Organisation` column. The names in this column will be matched against the Master file.

        **Troubleshooting Tips:**
        - **"No rows were updated" message:**
            - The most common reason is that the organisation names in the **Target File** do not match the names in the **Master File**. The matching is case-insensitive, but spelling, spacing, and punctuation must be identical (e.g., "Stripe" vs. "Stripe, Inc.").
            - Check if the `Sector` and `Category` fields in the target file are already filled. The script only fills in empty values.
        - **Error during processing:**
            - Ensure both uploaded files are valid, uncorrupted CSVs.
        """)

    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        master_file = st.file_uploader("1. Upload the MASTER file (with correct data)", type="csv")
    
    with col2:
        target_file = st.file_uploader("2. Upload the TARGET file to enrich", type="csv")
        
    if master_file is not None and target_file is not None:
        if st.button("Enrich Target File", type="primary"):
            with st.spinner("Building knowledge base and enriching file..."):
                master_string_io = io.StringIO(master_file.getvalue().decode("utf-8-sig"))
                target_string_io = io.StringIO(target_file.getvalue().decode("utf-8-sig"))
                
                output_csv, updated, total = enrich_from_master(master_string_io, target_string_io)
                
                st.success(f"**Enrichment complete!** {updated} out of {total} rows in the target file were updated.")
                
                file_base, _ = os.path.splitext(target_file.name)

                st.download_button(
                    label="⬇️ Download Enriched File",
                    data=output_csv,
                    file_name=f"{file_base}_enriched.csv",
                    mime="text/csv",
                )

st.sidebar.markdown("---")
st.sidebar.info("This app is powered by Streamlit.")