"""
Data Extractor for normalizing and extracting transaction data from tables
"""

import logging
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from utils import (
    map_column_to_standard,
    parse_date,
    parse_amount,
    categorize_transaction,
    validate_transaction_data,
    format_transaction_output,
    clean_text
)

logger = logging.getLogger(__name__)

class DataExtractor:
    """Extracts and normalizes transaction data from tables"""
    def __init__(self):
        pass

    def extract_closing_balance(self, text_content: List[str], tables: List[List[List[str]]]) -> Optional[float]:
        """
        Extract closing balance from text content and tables
        Returns the closing balance amount or None if not found
        """
        closing_balance = None
        
        # Method 1: Look for closing balance in text content
        for text in text_content:
            if not text:
                continue
                
            # Common patterns for closing balance
            patterns = [
                r'closing\s+balance[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'balance\s+as\s+on[^:]*[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'closing\s+amount[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'final\s+balance[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'balance\s+at\s+end[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'closing\s+bal[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'bal\s+as\s+on[^:]*[:\s]*rs?\.?\s*([\d,]+\.?\d*)',
                r'closing\s+balance\s*[:\s]*([\d,]+\.?\d*)',
                r'balance\s+as\s+on\s*[:\s]*([\d,]+\.?\d*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        # Clean the amount string and convert to float
                        amount_str = matches[0].replace(',', '')
                        closing_balance = float(amount_str)
                        logger.info(f"Found closing balance in text: {closing_balance}")
                        return closing_balance
                    except (ValueError, IndexError):
                        continue
        
        # Method 2: Look for closing balance in tables (summary tables)
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            # Look for summary tables that contain closing balance
            header = table[0]
            header_text = ' '.join([str(cell).lower() for cell in header if cell])
            
            # Check if this looks like a summary table
            summary_keywords = ['opening', 'closing', 'balance', 'summary', 'total']
            if any(keyword in header_text for keyword in summary_keywords):
                # Look for closing balance in the table
                for row in table[1:]:
                    if not row:
                        continue
                    
                    row_text = ' '.join([str(cell).lower() for cell in row if cell])
                    
                    # Look for closing balance row
                    if any(keyword in row_text for keyword in ['closing', 'balance as on', 'final']):
                        # Extract amount from this row
                        for cell in row:
                            if cell:
                                amount = parse_amount(cell)
                                if amount is not None:
                                    closing_balance = amount
                                    logger.info(f"Found closing balance in table: {closing_balance}")
                                    return closing_balance
        
        # Method 3: Look for balance in the last transaction row (if balance column exists)
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            header = table[0]
            balance_col_idx = None
            
            # Find balance column
            for idx, col in enumerate(header):
                if col and 'balance' in str(col).lower():
                    balance_col_idx = idx
                    break
            
            if balance_col_idx is not None:
                # Get the last non-empty balance value
                for row in reversed(table[1:]):
                    if row and len(row) > balance_col_idx and row[balance_col_idx]:
                        balance = parse_amount(row[balance_col_idx])
                        if balance is not None:
                            closing_balance = balance
                            logger.info(f"Found closing balance from last transaction: {closing_balance}")
                            return closing_balance
        
        if closing_balance is None:
            logger.warning("Could not find closing balance in the statement")
        
        return closing_balance

    def extract_transactions_from_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Extract transactions from a table (list of rows)"""
        transactions = []
        if not table or len(table) < 2:
            return transactions

        # Check if this is the specific format with S.No, Date, Transaction Id, Remarks, Debit, Credit
        header = table[0]
        header_text = ' '.join([str(cell).lower() for cell in header if cell])
        
        # Special handling for the third statement format
        if any(word in header_text for word in ['s.no', 'transaction id', 'remarks']):
            return self._extract_transactions_special_format(table)
        
        # Special handling for IDFC format (Transaction Date, Value Date, Particulars, Cheque No, Debit, Credit, Balance)
        if any(word in header_text for word in ['transaction date', 'value date', 'particulars']):
            return self._extract_transactions_idfc_format(table)
        
        # Special handling for simple format (Date, Description, Amount, Type)
        if any(word in header_text for word in ['date', 'description', 'amount', 'type']):
            return self._extract_transactions_simple_format(table)
        
        # Map columns to standard fields
        col_map = {}
        
        # First, try to map columns based on header
        for idx, col in enumerate(header):
            std_col = map_column_to_standard(col)
            if std_col:
                col_map[std_col] = idx

        # If we don't have all required fields, try to infer them
        required = ['date', 'description', 'amount']
        missing_fields = [field for field in required if field not in col_map]
        
        if missing_fields:
            logger.warning(f"Table header missing fields: {missing_fields}. Available columns: {header}")
            
            # Try to infer missing fields from available columns
            for field in missing_fields:
                if field == 'date':
                    # Look for any column that might contain dates
                    for idx, col in enumerate(header):
                        col_lower = str(col).lower()
                        if any(word in col_lower for word in ['date', 'dt', 'value', 'posting', 'transaction']):
                            col_map['date'] = idx
                            break
                elif field == 'description':
                    # Look for description-like columns
                    for idx, col in enumerate(header):
                        col_lower = str(col).lower()
                        if any(word in col_lower for word in ['desc', 'narration', 'particulars', 'details', 'memo', 'remarks', 'transaction id']):
                            col_map['description'] = idx
                            break
                elif field == 'amount':
                    # Look for amount-like columns
                    for idx, col in enumerate(header):
                        col_lower = str(col).lower()
                        if any(word in col_lower for word in ['amount', 'debit', 'credit', 'dr', 'cr', 'rs']):
                            col_map['amount'] = idx
                            break

        # Special handling for tables with separate debit/credit columns
        if 'amount' not in col_map:
            # Look for separate debit and credit columns
            debit_col = None
            credit_col = None
            for idx, col in enumerate(header):
                col_lower = str(col).lower()
                if any(word in col_lower for word in ['debit', 'dr', 'withdrawal']):
                    debit_col = idx
                elif any(word in col_lower for word in ['credit', 'cr', 'deposit']):
                    credit_col = idx
            
            if debit_col is not None or credit_col is not None:
                col_map['debit_col'] = debit_col
                col_map['credit_col'] = credit_col

        # Process each row
        for row_idx, row in enumerate(table[1:], 1):
            try:
                # Skip rows that are clearly not transactions
                if not row or len(row) < 2:
                    continue
                
                # Skip rows that are likely headers or summaries
                first_cell = str(row[0]).lower() if row[0] else ""
                if any(skip_word in first_cell for skip_word in ['opening', 'closing', 'total', 'balance', 'summary', 's.no']):
                    continue
                
                transaction = {}
                
                # Date
                if 'date' in col_map and col_map['date'] < len(row):
                    date_str = row[col_map['date']]
                    transaction['date'] = parse_date(date_str)
                else:
                    # Try to find date in any column
                    for cell in row:
                        if cell and parse_date(cell):
                            transaction['date'] = parse_date(cell)
                            break
                
                # Description
                if 'description' in col_map and col_map['description'] < len(row):
                    desc_str = row[col_map['description']]
                    transaction['description'] = clean_text(desc_str)
                else:
                    # Use the longest text field as description
                    longest_text = ""
                    for cell in row:
                        if cell and len(clean_text(cell)) > len(longest_text):
                            longest_text = clean_text(cell)
                    transaction['description'] = longest_text
                
                # Amount - handle both single amount column and separate debit/credit columns
                if 'amount' in col_map and col_map['amount'] < len(row):
                    amount_str = row[col_map['amount']]
                    transaction['amount'] = parse_amount(amount_str)
                elif 'debit_col' in col_map or 'credit_col' in col_map:
                    # Handle separate debit/credit columns
                    debit_amount = 0
                    credit_amount = 0
                    
                    if 'debit_col' in col_map and col_map['debit_col'] is not None and col_map['debit_col'] < len(row):
                        debit_str = row[col_map['debit_col']]
                        debit_amount = parse_amount(debit_str) or 0
                    
                    if 'credit_col' in col_map and col_map['credit_col'] is not None and col_map['credit_col'] < len(row):
                        credit_str = row[col_map['credit_col']]
                        credit_amount = parse_amount(credit_str) or 0
                    
                    # Use the non-zero amount (debit is negative, credit is positive)
                    if debit_amount != 0:
                        transaction['amount'] = -abs(debit_amount)
                    elif credit_amount != 0:
                        transaction['amount'] = abs(credit_amount)
                    else:
                        continue  # Skip if no amount found
                else:
                    # Try to find amount in any column
                    for cell in row:
                        if cell and parse_amount(cell) is not None:
                            transaction['amount'] = parse_amount(cell)
                            break
                
                # Balance (optional)
                if 'balance' in col_map and col_map['balance'] < len(row):
                    transaction['balance'] = parse_amount(row[col_map['balance']])
                
                # Category (optional)
                transaction['category'] = categorize_transaction(transaction.get('description', ''))
                
                # Validate and add transaction
                if validate_transaction_data(transaction):
                    transactions.append(format_transaction_output(transaction))
                else:
                    logger.debug(f"Skipping invalid transaction at row {row_idx}: {row}")
                    
            except Exception as e:
                logger.warning(f"Error parsing row {row_idx} {row}: {e}")
        
        return transactions

    def _extract_transactions_special_format(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Extract transactions from the special format (S.No, Date, Transaction Id, Remarks, Debit, Credit)"""
        transactions = []
        
        for row_idx, row in enumerate(table[1:], 1):
            try:
                # Skip rows that are clearly not transactions
                if not row or len(row) < 4:
                    continue
                
                # Skip rows that are likely headers or summaries
                first_cell = str(row[0]).lower() if row[0] else ""
                if any(skip_word in first_cell for skip_word in ['opening', 'closing', 'total', 'balance', 'summary']):
                    continue
                
                transaction = {}
                
                # Date (column 1)
                if len(row) > 1 and row[1]:
                    transaction['date'] = parse_date(str(row[1]))
                
                # Description (column 3 - Remarks)
                if len(row) > 3 and row[3]:
                    transaction['description'] = clean_text(str(row[3]))
                elif len(row) > 2 and row[2]:  # Fallback to Transaction Id
                    transaction['description'] = clean_text(str(row[2]))
                
                # Amount - handle separate debit/credit columns
                debit_amount = 0
                credit_amount = 0
                
                # Debit (column 4)
                if len(row) > 4 and row[4]:
                    debit_amount = parse_amount(str(row[4])) or 0
                
                # Credit (column 5)
                if len(row) > 5 and row[5]:
                    credit_amount = parse_amount(str(row[5])) or 0
                
                # Use the non-zero amount (debit is negative, credit is positive)
                if debit_amount != 0:
                    transaction['amount'] = -abs(debit_amount)
                elif credit_amount != 0:
                    transaction['amount'] = abs(credit_amount)
                else:
                    continue  # Skip if no amount found
                
                # Category (optional)
                transaction['category'] = categorize_transaction(transaction.get('description', ''))
                
                # Validate and add transaction
                if validate_transaction_data(transaction):
                    transactions.append(format_transaction_output(transaction))
                else:
                    logger.debug(f"Skipping invalid transaction at row {row_idx}: {row}")
                    
            except Exception as e:
                logger.warning(f"Error parsing row {row_idx} {row}: {e}")
        
        return transactions

    def _extract_transactions_idfc_format(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Extract transactions from IDFC format (Transaction Date, Value Date, Particulars, Cheque No, Debit, Credit, Balance)"""
        transactions = []
        
        for row_idx, row in enumerate(table[1:], 1):
            try:
                # Skip rows that are clearly not transactions
                if not row or len(row) < 4:
                    continue
                
                # Skip rows that are likely headers or summaries
                first_cell = str(row[0]).lower() if row[0] else ""
                if any(skip_word in first_cell for skip_word in ['opening', 'closing', 'total', 'balance', 'summary']):
                    continue
                
                transaction = {}
                
                # Date (column 0 - Transaction Date)
                if len(row) > 0 and row[0]:
                    transaction['date'] = parse_date(str(row[0]))
                
                # Description (column 2 - Particulars)
                if len(row) > 2 and row[2]:
                    transaction['description'] = clean_text(str(row[2]))
                
                # Amount - handle separate debit/credit columns
                debit_amount = 0
                credit_amount = 0
                
                # Debit (column 4)
                if len(row) > 4 and row[4]:
                    debit_amount = parse_amount(str(row[4])) or 0
                
                # Credit (column 5)
                if len(row) > 5 and row[5]:
                    credit_amount = parse_amount(str(row[5])) or 0
                
                # Use the non-zero amount (debit is negative, credit is positive)
                if debit_amount != 0:
                    transaction['amount'] = -abs(debit_amount)
                elif credit_amount != 0:
                    transaction['amount'] = abs(credit_amount)
                else:
                    continue  # Skip if no amount found
                
                # Balance (column 6)
                if len(row) > 6 and row[6]:
                    transaction['balance'] = parse_amount(str(row[6]))
                
                # Category (optional)
                transaction['category'] = categorize_transaction(transaction.get('description', ''))
                
                # Validate and add transaction
                if validate_transaction_data(transaction):
                    transactions.append(format_transaction_output(transaction))
                else:
                    logger.debug(f"Skipping invalid transaction at row {row_idx}: {row}")
                    
            except Exception as e:
                logger.warning(f"Error parsing row {row_idx} {row}: {e}")
        
        return transactions

    def _extract_transactions_simple_format(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Extract transactions from simple format (Date, Description, Amount, Type)"""
        transactions = []
        
        for row_idx, row in enumerate(table[1:], 1):
            try:
                # Skip rows that are clearly not transactions
                if not row or len(row) < 3:
                    continue
                
                transaction = {}
                
                # Date (column 0)
                if len(row) > 0 and row[0]:
                    transaction['date'] = parse_date(str(row[0]))
                
                # Description (column 1)
                if len(row) > 1 and row[1]:
                    transaction['description'] = clean_text(str(row[1]))
                
                # Amount (column 2)
                if len(row) > 2 and row[2]:
                    amount = parse_amount(str(row[2])) or 0
                    
                    # Check type (column 3) to determine if it's debit or credit
                    if len(row) > 3 and row[3]:
                        txn_type = str(row[3]).upper()
                        if 'DR' in txn_type or 'DEBIT' in txn_type:
                            amount = -abs(amount)
                        elif 'CR' in txn_type or 'CREDIT' in txn_type:
                            amount = abs(amount)
                    
                    transaction['amount'] = amount
                else:
                    continue  # Skip if no amount found
                
                # Category (optional)
                transaction['category'] = categorize_transaction(transaction.get('description', ''))
                
                # Validate and add transaction
                if validate_transaction_data(transaction):
                    transactions.append(format_transaction_output(transaction))
                else:
                    logger.debug(f"Skipping invalid transaction at row {row_idx}: {row}")
                    
            except Exception as e:
                logger.warning(f"Error parsing row {row_idx} {row}: {e}")
        
        return transactions

    def extract_transactions_from_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract transactions from a pandas DataFrame"""
        transactions = []
        if df.empty:
            return transactions
        # Map columns
        col_map = {}
        for col in df.columns:
            std_col = map_column_to_standard(col)
            if std_col:
                col_map[std_col] = col
        required = ['date', 'description', 'amount']
        if not all(field in col_map for field in required):
            logger.warning(f"DataFrame missing required fields: {df.columns}")
            return transactions
        for _, row in df.iterrows():
            try:
                transaction = {}
                transaction['date'] = parse_date(str(row[col_map['date']]))
                transaction['description'] = clean_text(str(row[col_map['description']]))
                transaction['amount'] = parse_amount(str(row[col_map['amount']]))
                if 'balance' in col_map:
                    transaction['balance'] = parse_amount(str(row[col_map['balance']]))
                transaction['category'] = categorize_transaction(transaction['description'])
                if validate_transaction_data(transaction):
                    transactions.append(format_transaction_output(transaction))
            except Exception as e:
                logger.warning(f"Error parsing row {row}: {e}")
        return transactions 