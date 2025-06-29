"""
PDF Processor for extracting data from native and scanned PDFs
"""

import logging
import pdfplumber
import PyPDF2
from pdf2image import convert_from_path
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import os

from config import PDF_CONFIG
from ocr_processor import OCRProcessor
from utils import clean_text, extract_table_from_text

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF parsing for both native and scanned PDFs"""
    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.pdf_config = PDF_CONFIG

    def is_scanned_pdf(self, file_path: str) -> bool:
        """Heuristically determine if a PDF is scanned (image-based) or native (text-based)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    if page.extract_text():
                        return False  # Found text, likely native
            return True  # No text found, likely scanned
        except Exception as e:
            logger.warning(f"Error checking if PDF is scanned: {e}")
            return True  # Assume scanned if error

    def is_transaction_table(self, table: List[List[str]]) -> bool:
        """Determine if a table is likely to contain transaction data"""
        if not table or len(table) < 2:
            return False
        
        # Get header row
        header = table[0]
        header_text = ' '.join([str(cell).lower() for cell in header if cell])
        
        # Check for transaction-related keywords in header
        transaction_keywords = [
            'date', 'description', 'narration', 'particulars', 'details',
            'debit', 'credit', 'amount', 'balance', 'transaction',
            'value date', 'posting date', 'cheque no', 'ref no',
            'remarks', 'transaction id', 's.no'  # Added for third statement
        ]
        
        has_transaction_keywords = any(keyword in header_text for keyword in transaction_keywords)
        
        # Check if table has reasonable number of rows (transactions are usually many rows)
        has_reasonable_rows = len(table) >= 3
        
        # Check if table has reasonable number of columns (transactions usually have 3-8 columns)
        has_reasonable_cols = 2 <= len(header) <= 10
        
        # Check for summary table indicators (these are NOT transaction tables)
        summary_indicators = [
            'opening balance', 'closing balance', 'total debit', 'total credit',
            'summary', 'glossary', 'abbreviations', 'atm', 'neft', 'rtgs', 'upi',
            'a2a', 'account to account', 'scan the qr code', 'details of statement'
        ]
        
        is_summary_table = any(indicator in header_text for indicator in summary_indicators)
        
        # Check if table contains mostly numeric data in amount columns
        has_numeric_data = False
        if len(table) > 1:
            sample_rows = table[1:min(5, len(table))]  # Check first few rows
            numeric_count = 0
            total_cells = 0
            
            for row in sample_rows:
                for cell in row:
                    if cell:
                        total_cells += 1
                        # Check if cell looks like an amount (contains digits and possibly commas/decimals)
                        import re
                        if re.search(r'\d', str(cell)) and re.search(r'[\d,\.]+', str(cell)):
                            numeric_count += 1
            
            if total_cells > 0:
                has_numeric_data = (numeric_count / total_cells) > 0.2  # Reduced threshold to 20%
        
        # Check for date patterns in the first few rows
        has_date_patterns = False
        if len(table) > 1:
            import re
            date_pattern = re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2}\d{2}\d{4}')
            for i in range(1, min(4, len(table))):
                row_text = ' '.join([str(cell) for cell in table[i] if cell])
                if date_pattern.search(row_text):
                    has_date_patterns = True
                    break
        
        # A table is likely a transaction table if:
        # 1. Has transaction keywords in header OR has reasonable structure
        # 2. Has reasonable structure
        # 3. Is NOT a summary table
        # 4. Has some numeric data OR has date-like patterns
        return ((has_transaction_keywords or has_reasonable_cols) and 
                has_reasonable_rows and 
                not is_summary_table and
                (has_numeric_data or has_date_patterns))

    def extract_text_from_native_pdf(self, file_path: str) -> List[str]:
        """Extract text from each page of a native PDF"""
        texts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    texts.append(clean_text(text))
        except Exception as e:
            logger.error(f"Error extracting text from native PDF: {e}")
        return texts

    def convert_pdf_to_images(self, file_path: str) -> List[str]:
        """Convert each page of a PDF to an image and return image paths"""
        image_paths = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_path(
                    file_path,
                    dpi=self.pdf_config['ocr_settings']['dpi'],
                    fmt=self.pdf_config['ocr_settings']['format']
                )
                for i, image in enumerate(images):
                    img_path = os.path.join(temp_dir, f"page_{i+1}.png")
                    image.save(img_path, 'PNG')
                    image_paths.append(img_path)
                # Copy images to a persistent location if needed
                # For now, return temp paths
                return list(image_paths)
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
        return image_paths

    def extract_text_from_scanned_pdf(self, file_path: str) -> List[str]:
        """Extract text from each page of a scanned PDF using OCR"""
        texts = []
        image_paths = self.convert_pdf_to_images(file_path)
        for img_path in image_paths:
            text = self.ocr_processor.extract_text_from_image(img_path)
            texts.append(text)
        return texts

    def extract_tables_from_pdf(self, file_path: str, scanned: Optional[bool] = None) -> List[List[List[str]]]:
        """Extract tables from PDF (native or scanned)"""
        tables = []
        if scanned is None:
            scanned = self.is_scanned_pdf(file_path)
        if not scanned:
            # Native PDF: use pdfplumber to extract tables
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        page_tables = page.extract_tables()
                        for table_num, table in enumerate(page_tables):
                            if table:
                                # Clean table rows
                                cleaned_table = [[clean_text(cell) if cell else "" for cell in row] for row in table]
                                # Filter for transaction tables only
                                if self.is_transaction_table(cleaned_table):
                                    logger.info(f"Found transaction table on page {page_num + 1}, table {table_num + 1} with {len(cleaned_table)} rows")
                                    tables.append(cleaned_table)
                                else:
                                    logger.debug(f"Skipping non-transaction table on page {page_num + 1}, table {table_num + 1}")
            except Exception as e:
                logger.error(f"Error extracting tables from native PDF: {e}")
        else:
            # Scanned PDF: OCR each page image
            image_paths = self.convert_pdf_to_images(file_path)
            for img_path in image_paths:
                page_tables = self.ocr_processor.extract_tables_from_image(img_path)
                for table in page_tables:
                    if self.is_transaction_table(table):
                        tables.append(table)
        return tables

    def extract_text(self, file_path: str) -> List[str]:
        """Extract text from PDF, auto-detecting scanned/native"""
        if self.is_scanned_pdf(file_path):
            return self.extract_text_from_scanned_pdf(file_path)
        else:
            return self.extract_text_from_native_pdf(file_path) 