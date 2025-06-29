"""
CLI entry point for the Bank Statement Parser AI Agent
"""

import argparse
import logging
from bank_parser import BankStatementParser

logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Bank Statement Parser AI Agent")
    parser.add_argument('--file', type=str, required=True, help='Path to the bank statement file (PDF or Excel)')
    parser.add_argument('--output', type=str, default=None, help='Path to save the parsed output (optional)')
    args = parser.parse_args()

    agent = BankStatementParser()
    result = agent.parse_file_with_balance(args.file)
    
    transactions = result['transactions']
    closing_balance = result['closing_balance']
    
    if not transactions:
        print("No transactions found or failed to parse the file.")
        return
    
    print(f"Parsed {len(transactions)} transactions.")
    
    if closing_balance is not None:
        print(f"Closing Balance: ₹{closing_balance:,.2f}")
    else:
        print("Closing balance not found in the statement.")
    
    output_path = agent.save_parsed_output(transactions, args.output, closing_balance)
    print(f"Output saved to: {output_path}")

if __name__ == '__main__':
    main() 