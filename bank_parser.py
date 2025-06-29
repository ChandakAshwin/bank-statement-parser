"""
BankStatementParser: Main orchestrator for parsing bank statements
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from utils import (
    validate_file_path,
    is_supported_file,
    get_file_extension,
    save_output
)
from pdf_processor import PDFProcessor
from excel_processor import ExcelProcessor
from data_extractor import DataExtractor
from config import OUTPUT_CONFIG
import pandas as pd

logger = logging.getLogger(__name__)

class BankStatementParser:
    """Main AI agent for parsing bank statements"""
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.excel_processor = ExcelProcessor()
        self.data_extractor = DataExtractor()

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a bank statement file and return structured transactions"""
        result = self.parse_file_with_balance(file_path)
        return result['transactions']

    def parse_file_with_balance(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a bank statement file and return structured transactions along with closing balance
        Returns: {'transactions': List[Dict], 'closing_balance': Optional[float]}
        """
        if not validate_file_path(file_path):
            logger.error(f"File not found: {file_path}")
            return {'transactions': [], 'closing_balance': None}
        
        if not is_supported_file(file_path):
            logger.error(f"Unsupported file type: {file_path}")
            return {'transactions': [], 'closing_balance': None}
        
        ext = get_file_extension(file_path)
        transactions = []
        text_content = []
        all_tables = []
        
        if ext == '.pdf':
            # PDF: extract tables (native or scanned)
            all_tables = self.pdf_processor.extract_tables_from_pdf(file_path)
            text_content = self.pdf_processor.extract_text(file_path)
            
            for table in all_tables:
                txns = self.data_extractor.extract_transactions_from_table(table)
                transactions.extend(txns)
                
        elif ext in ['.xls', '.xlsx', '.xlsm']:
            # Excel: extract tables
            excel_tables = self.excel_processor.extract_tables_from_excel(file_path)
            # For Excel, we'll use table content as text content for balance extraction
            for table in excel_tables:
                if table is not None and not table.empty:
                    text_content.append(' '.join([str(cell) for cell in table.values.flatten() if pd.notna(cell)]))
                    txns = self.data_extractor.extract_transactions_from_dataframe(table)
                    transactions.extend(txns)
                    # Convert DataFrame to list format for balance extraction
                    table_list = [table.columns.tolist()] + table.values.tolist()
                    all_tables.append(table_list)
        else:
            logger.error(f"Unsupported file extension: {ext}")
            return {'transactions': [], 'closing_balance': None}
        
        # Extract closing balance
        closing_balance = self.data_extractor.extract_closing_balance(text_content, all_tables)
        
        return {
            'transactions': transactions,
            'closing_balance': closing_balance
        }

    def save_parsed_output(self, transactions: List[Dict[str, Any]], output_path: Optional[str] = None, closing_balance: Optional[float] = None) -> str:
        """Save parsed transactions to file (json/csv/excel) with optional closing balance"""
        if not transactions and closing_balance is None:
            logger.warning("No transactions or closing balance to save.")
            return ""
        
        if output_path is None:
            output_path = str(Path.cwd() / f"parsed_output.{OUTPUT_CONFIG['output_format']}")
        
        # If we have closing balance, include it in the output
        if closing_balance is not None:
            # Add closing balance as a summary entry
            summary_data = {
                'transactions': transactions,
                'summary': {
                    'total_transactions': len(transactions),
                    'closing_balance': closing_balance
                }
            }
            # For structured output with summary, save as JSON
            import json
            with open(output_path, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
        else:
            save_output(transactions, output_path, format=OUTPUT_CONFIG['output_format'])
        
        return output_path 