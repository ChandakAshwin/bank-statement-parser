"""
Streamlit web interface for the Bank Statement Parser AI Agent
"""

import streamlit as st
import tempfile
import os
import json
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
    result = agent.parse_file_with_balance(tmp_path)
    
    transactions = result['transactions']
    closing_balance = result['closing_balance']
    
    if not transactions:
        st.error("No transactions found or failed to parse the file.")
    else:
        st.success(f"Parsed {len(transactions)} transactions!")
        
        # Display closing balance if found
        if closing_balance is not None:
            st.metric("Closing Balance", f"₹{closing_balance:,.2f}")
        else:
            st.warning("Closing balance not found in the statement.")
        
        # Display transactions
        st.subheader("Transactions")
        st.dataframe(transactions)
        
        # Create summary data for download
        summary_data = {
            'transactions': transactions,
            'summary': {
                'total_transactions': len(transactions),
                'closing_balance': closing_balance
            }
        }
        
        # Download button for complete data
        st.download_button(
            label="Download Complete Data (JSON)",
            data=json.dumps(summary_data, indent=2, default=str),
            file_name="parsed_statement_with_balance.json",
            mime="application/json"
        )
        
        # Download button for transactions only
        st.download_button(
            label="Download Transactions Only (JSON)",
            data=json.dumps(transactions, indent=2, default=str),
            file_name="parsed_transactions.json",
            mime="application/json"
        )
    
    os.remove(tmp_path)
else:
    st.info("Please upload a PDF or Excel bank statement to begin.") 