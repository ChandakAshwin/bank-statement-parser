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
    transactions = agent.parse_file(args.file)
    if not transactions:
        print("No transactions found or failed to parse the file.")
        return
    output_path = agent.save_parsed_output(transactions, args.output)
    print(f"Parsed {len(transactions)} transactions. Output saved to: {output_path}")

if __name__ == '__main__':
    main() 