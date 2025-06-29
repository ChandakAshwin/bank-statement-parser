#!/usr/bin/env python3
"""
Test script for closing balance functionality
"""

import logging
from data_extractor import DataExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_balance_extraction():
    """Test the closing balance extraction functionality with mock data"""
    print("Testing closing balance extraction with mock data...")
    
    extractor = DataExtractor()
    
    # Mock text content with closing balance
    mock_text = [
        "Bank Statement for Account 123456789",
        "Opening Balance: Rs. 50,000.00",
        "Closing Balance: Rs. 75,250.50",
        "Total transactions: 25"
    ]
    
    # Mock table with balance column
    mock_table = [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["01/01/2024", "Salary", "", "25,000.00", "75,000.00"],
        ["02/01/2024", "ATM Withdrawal", "500.00", "", "74,500.00"],
        ["03/01/2024", "Online Payment", "750.50", "", "73,749.50"],
        ["04/01/2024", "Interest Credit", "", "1,501.00", "75,250.50"]
    ]
    
    # Test closing balance extraction
    closing_balance = extractor.extract_closing_balance(mock_text, [mock_table])
    
    print(f"Extracted closing balance: {closing_balance}")
    
    if closing_balance == 75250.50:
        print("✅ Closing balance extraction working correctly!")
    else:
        print(f"❌ Expected 75250.50, got {closing_balance}")
    
    # Test with different text patterns
    print("\nTesting different text patterns...")
    
    patterns = [
        "Closing Balance: 1,25,000.00",
        "Balance as on 31/12/2023: Rs. 2,50,000.50",
        "Final Balance: 75,500.00",
        "Closing Amount: 1,00,000.00"
    ]
    
    for pattern in patterns:
        balance = extractor.extract_closing_balance([pattern], [])
        print(f"Pattern: '{pattern}' -> Balance: {balance}")

if __name__ == "__main__":
    test_balance_extraction() 