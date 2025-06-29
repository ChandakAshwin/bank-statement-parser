"""
Excel Processor for extracting data from Excel bank statements
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from config import EXCEL_CONFIG
from utils import clean_text, clean_dataframe

logger = logging.getLogger(__name__)

class ExcelProcessor:
    """Handles Excel file parsing for bank statements"""
    def __init__(self):
        self.config = EXCEL_CONFIG

    def extract_tables_from_excel(self, file_path: str) -> List[pd.DataFrame]:
        """Extract tables (as DataFrames) from Excel file"""
        tables = []
        try:
            # Read all sheets
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(
                    xls,
                    sheet_name=sheet_name,
                    header=self.config['header'],
                    skiprows=self.config['skiprows'],
                    na_values=self.config['na_values']
                )
                df = clean_dataframe(df)
                if not df.empty:
                    tables.append(df)
        except Exception as e:
            logger.error(f"Error extracting tables from Excel: {e}")
        return tables

    def extract_text_from_excel(self, file_path: str) -> List[str]:
        """Extract text from Excel file (row-wise)"""
        texts = []
        try:
            tables = self.extract_tables_from_excel(file_path)
            for df in tables:
                for _, row in df.iterrows():
                    row_text = ' | '.join([clean_text(str(cell)) for cell in row if pd.notna(cell)])
                    if row_text:
                        texts.append(row_text)
        except Exception as e:
            logger.error(f"Error extracting text from Excel: {e}")
        return texts 