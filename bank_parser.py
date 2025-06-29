"""
BankStatementParser: Main orchestrator for parsing bank statements
"""

import logging
from typing import List, Dict, Any, Optional
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

logger = logging.getLogger(__name__)

class BankStatementParser:
    """Main AI agent for parsing bank statements"""
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.excel_processor = ExcelProcessor()
        self.data_extractor = DataExtractor()

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a bank statement file and return structured transactions"""
        if not validate_file_path(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        if not is_supported_file(file_path):
            logger.error(f"Unsupported file type: {file_path}")
            return []
        ext = get_file_extension(file_path)
        transactions = []
        if ext == '.pdf':
            # PDF: extract tables (native or scanned)
            tables = self.pdf_processor.extract_tables_from_pdf(file_path)
            for table in tables:
                txns = self.data_extractor.extract_transactions_from_table(table)
                transactions.extend(txns)
        elif ext in ['.xls', '.xlsx', '.xlsm']:
            # Excel: extract tables
            tables = self.excel_processor.extract_tables_from_excel(file_path)
            for df in tables:
                txns = self.data_extractor.extract_transactions_from_dataframe(df)
                transactions.extend(txns)
        else:
            logger.error(f"Unsupported file extension: {ext}")
        return transactions

    def save_parsed_output(self, transactions: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """Save parsed transactions to file (json/csv/excel)"""
        if not transactions:
            logger.warning("No transactions to save.")
            return ""
        if output_path is None:
            output_path = str(Path.cwd() / f"parsed_output.{OUTPUT_CONFIG['output_format']}")
        save_output(transactions, output_path, format=OUTPUT_CONFIG['output_format'])
        return output_path 