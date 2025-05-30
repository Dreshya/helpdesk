import patch_streamlit
import streamlit as st
import tempfile
from preprocessor import process_and_store_xml

st.set_page_config(page_title="XML Vector Uploader", layout="centered")
st.title("📂 Upload XML File and Store in ChromaDB")

uploaded_file = st.file_uploader("Upload your XML file", type="xml")
st.subheader("📝 Document ID")
doc_id = st.text_input("Enter a unique ID for this document (required)", value="")

if st.button("Process File"):
    if uploaded_file is None:
        st.error("⚠️ Please upload an XML file.")
    elif not doc_id.strip():
        st.error("⚠️ Please enter a valid document ID.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        st.info(f"Processing `{uploaded_file.name}` with ID `{doc_id}`...")
        try:
            chunks = process_and_store_xml(tmp_path, doc_id=doc_id.strip())
            st.success(f"✅ File processed and {len(chunks)} chunks stored in ChromaDB!")
            
            st.subheader("🔍 Last Chunk Preview")
            st.text_area(label="Chunk Preview", value=chunks[-1] if chunks else "", height=200)
        except Exception as e:
            st.error(f"⚠️ Error processing file: {e}")
