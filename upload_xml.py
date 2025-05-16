# app.py
import patch_streamlit
import streamlit as st
import tempfile
from preprocessor import process_and_store_xml


st.set_page_config(page_title="XML Vector Uploader", layout="centered")
st.title("📂 Upload XML File and Store in ChromaDB")

uploaded_file = st.file_uploader("Upload your XML file", type="xml")

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.info(f"Processing `{uploaded_file.name}`...")
    chunks = process_and_store_xml(tmp_path)
    st.success(f"✅ File processed and {len(chunks)} chunks stored in ChromaDB!")

    st.subheader("🔍 Last Chunk Preview")
    st.text_area(label="Chunk Preview", value=chunks[-1], height=200)
