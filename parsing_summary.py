#!/usr/bin/env python3
"""
Analyze and summarize the parsed bank statement
"""

import json
from collections import defaultdict
from datetime import datetime

def analyze_statement(filename):
    """Analyze the parsed bank statement"""
    with open(filename, 'r') as f:
        transactions = json.load(f)
    
    print(f"📊 Bank Statement Analysis")
    print("=" * 50)
    print(f"Total Transactions: {len(transactions)}")
    
    # Date range
    dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in transactions]
    start_date = min(dates)
    end_date = max(dates)
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Transaction types
    debit_count = sum(1 for t in transactions if t['debit_credit'] == 'debit')
    credit_count = sum(1 for t in transactions if t['debit_credit'] == 'credit')
    print(f"Debits: {debit_count}, Credits: {credit_count}")
    
    # Total amounts
    total_debits = sum(t['amount'] for t in transactions if t['amount'] < 0)
    total_credits = sum(t['amount'] for t in transactions if t['amount'] > 0)
    print(f"Total Debits: ₹{abs(total_debits):,.2f}")
    print(f"Total Credits: ₹{total_credits:,.2f}")
    print(f"Net Change: ₹{total_credits + total_debits:,.2f}")
    
    # Categories
    categories = defaultdict(int)
    for t in transactions:
        category = t.get('category', 'uncategorized')
        categories[category] += 1
    
    print(f"\n📈 Transaction Categories:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} transactions")
    
    # Top transactions by amount
    print(f"\n💰 Top 5 Transactions by Amount:")
    sorted_by_amount = sorted(transactions, key=lambda x: abs(x['amount']), reverse=True)
    for i, t in enumerate(sorted_by_amount[:5], 1):
        print(f"  {i}. {t['date']} - {t['description'][:50]}... - ₹{t['amount']:,.2f}")
    
    # Balance analysis
    if transactions:
        initial_balance = transactions[0]['balance'] - transactions[0]['amount']
        final_balance = transactions[-1]['balance']
        print(f"\n💳 Balance Analysis:")
        print(f"  Opening Balance: ₹{initial_balance:,.2f}")
        print(f"  Closing Balance: ₹{final_balance:,.2f}")
        print(f"  Net Change: ₹{final_balance - initial_balance:,.2f}")

if __name__ == "__main__":
    analyze_statement('parsed_idfc_statement.json') 