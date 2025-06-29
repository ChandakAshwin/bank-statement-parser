"""
Streamlit web interface for the Bank Statement Parser AI Agent
"""

import streamlit as st
import tempfile
import os
from bank_parser import BankStatementParser

st.set_page_config(page_title="Bank Statement Parser AI Agent", layout="centered")
st.title("🏦 Bank Statement Parser AI Agent")
st.write("Upload your bank statement (PDF or Excel) and extract structured transaction data.")

uploaded_file = st.file_uploader("Choose a bank statement file (PDF, XLS, XLSX)", type=["pdf", "xls", "xlsx", "xlsm"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name
    st.info(f"Processing file: {uploaded_file.name}")
    agent = BankStatementParser()
    transactions = agent.parse_file(tmp_path)
    if not transactions:
        st.error("No transactions found or failed to parse the file.")
    else:
        st.success(f"Parsed {len(transactions)} transactions!")
        st.dataframe(transactions)
        st.download_button(
            label="Download as JSON",
            data=str(transactions),
            file_name="parsed_transactions.json",
            mime="application/json"
        )
    os.remove(tmp_path)
else:
    st.info("Please upload a PDF or Excel bank statement to begin.") 