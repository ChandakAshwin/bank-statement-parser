"""
Utility functions for the Bank Statement Parser AI Agent
"""

import re
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import chardet
from config import DATE_FORMATS, COLUMN_MAPPINGS, TRANSACTION_CATEGORIES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_logging(log_file: Optional[str] = None, level: str = 'INFO'):
    """Set up logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format
        )


def validate_file_path(file_path: str) -> bool:
    """Validate if file exists and is accessible"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception as e:
        logger.error(f"Error validating file path {file_path}: {e}")
        return False


def get_file_extension(file_path: str) -> str:
    """Get file extension in lowercase"""
    return Path(file_path).suffix.lower()


def is_supported_file(file_path: str) -> bool:
    """Check if file type is supported"""
    from config import SUPPORTED_EXTENSIONS
    ext = get_file_extension(file_path)
    return ext in SUPPORTED_EXTENSIONS['all']


def detect_encoding(file_path: str) -> str:
    """Detect file encoding"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except Exception as e:
        logger.warning(f"Could not detect encoding for {file_path}: {e}")
        return 'utf-8'


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters that might interfere with parsing
    text = re.sub(r'[^\w\s\-.,$()]', '', text)
    return text


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string using multiple formats"""
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = clean_text(date_str)
    
    # Try different date formats
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try to extract date using regex patterns
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY/MM/DD
        r'(\d{1,2})-([A-Za-z]{3})-(\d{4})',      # DD-MMM-YYYY (like 01-Mar-2025)
        r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})',  # DD MMM YYYY
        r'(\d{2})(\d{2})(\d{4})',                # DDMMYYYY (like 20052025)
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                if len(match.group(3)) == 2:  # 2-digit year
                    year = int(match.group(3))
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                else:
                    year = int(match.group(3))
                
                # Handle month names
                if match.group(2).isalpha():
                    month_names = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    month = month_names.get(match.group(2).lower()[:3])
                    if not month:
                        continue
                else:
                    month = int(match.group(2))
                
                day = int(match.group(1))
                
                return datetime(year, month, day)
            except (ValueError, IndexError):
                continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def parse_amount(amount_str: str) -> Optional[float]:
    """Parse amount string to float"""
    if not amount_str or not isinstance(amount_str, str):
        return None
    
    # Clean the amount string
    amount_str = clean_text(amount_str)
    
    # Handle Dr/Cr suffixes (common in Indian bank statements)
    is_negative = False
    if 'dr' in amount_str.lower():
        is_negative = True
        amount_str = re.sub(r'\s*dr\s*', '', amount_str, flags=re.IGNORECASE)
    elif 'cr' in amount_str.lower():
        is_negative = False
        amount_str = re.sub(r'\s*cr\s*', '', amount_str, flags=re.IGNORECASE)
    
    # Remove currency symbols and commas
    amount_str = re.sub(r'[$,€£¥₹]', '', amount_str)
    amount_str = re.sub(r',', '', amount_str)
    
    # Handle parentheses (negative amounts)
    if '(' in amount_str and ')' in amount_str:
        is_negative = True
        amount_str = re.sub(r'[()]', '', amount_str)
    
    # Remove any remaining non-numeric characters except decimal point
    amount_str = re.sub(r'[^\d.-]', '', amount_str)
    
    try:
        amount = float(amount_str)
        return -amount if is_negative else amount
    except ValueError:
        logger.warning(f"Could not parse amount: {amount_str}")
        return None


def normalize_column_name(column_name: str) -> str:
    """Normalize column name for consistent mapping"""
    if not column_name:
        return ""
    
    # Convert to lowercase and clean
    normalized = clean_text(column_name.lower())
    
    # Remove common prefixes/suffixes
    normalized = re.sub(r'^(the\s+|a\s+|an\s+)', '', normalized)
    normalized = re.sub(r'(\s+amount|\s+date|\s+description|\s+balance)$', '', normalized)
    
    return normalized


def map_column_to_standard(column_name: str) -> Optional[str]:
    """Map column name to standard field name"""
    normalized = normalize_column_name(column_name)
    
    # Direct exact matches
    for standard_field, variations in COLUMN_MAPPINGS.items():
        for variation in variations:
            if variation == normalized:
                return standard_field
    
    # Partial matches (more flexible)
    for standard_field, variations in COLUMN_MAPPINGS.items():
        for variation in variations:
            # Check if variation is contained in normalized or vice versa
            if variation in normalized or normalized in variation:
                return standard_field
            
            # Check for word-based matches
            normalized_words = set(normalized.split())
            variation_words = set(variation.split())
            if normalized_words & variation_words:  # Intersection
                return standard_field
    
    # Special handling for common bank-specific patterns
    if any(word in normalized for word in ['date', 'dt']):
        return 'date'
    elif any(word in normalized for word in ['desc', 'narration', 'particulars', 'details']):
        return 'description'
    elif any(word in normalized for word in ['amount', 'debit', 'credit', 'dr', 'cr']):
        return 'amount'
    elif any(word in normalized for word in ['balance', 'bal']):
        return 'balance'
    
    return None


def categorize_transaction(description: str) -> Optional[str]:
    """Categorize transaction based on description"""
    if not description:
        return None
    
    description_lower = description.lower()
    
    for category, keywords in TRANSACTION_CATEGORIES.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    
    return None


def validate_transaction_data(transaction: Dict[str, Any]) -> bool:
    """Validate transaction data structure"""
    required_fields = ['date', 'description', 'amount']
    
    for field in required_fields:
        if field not in transaction or transaction[field] is None:
            return False
    
    # Validate date
    if not isinstance(transaction['date'], datetime):
        return False
    
    # Validate amount
    if not isinstance(transaction['amount'], (int, float)):
        return False
    
    # Validate description
    if not isinstance(transaction['description'], str) or not transaction['description'].strip():
        return False
    
    return True


def format_transaction_output(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Format transaction for output"""
    from config import OUTPUT_CONFIG
    
    formatted = {
        'date': transaction['date'].strftime(OUTPUT_CONFIG['date_format']),
        'description': clean_text(transaction['description']),
        'amount': round(transaction['amount'], OUTPUT_CONFIG['amount_precision']),
        'debit_credit': 'debit' if transaction['amount'] < 0 else 'credit'
    }
    
    # Add balance if available
    if 'balance' in transaction and transaction['balance'] is not None:
        formatted['balance'] = round(transaction['balance'], OUTPUT_CONFIG['amount_precision'])
    
    # Add category if enabled and available
    if OUTPUT_CONFIG['include_category']:
        if 'category' in transaction and transaction['category']:
            formatted['category'] = transaction['category']
        else:
            formatted['category'] = categorize_transaction(transaction['description'])
    
    return formatted


def save_output(data: List[Dict[str, Any]], output_path: str, format: str = 'json'):
    """Save parsed data to file"""
    try:
        if format.lower() == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format.lower() == 'csv':
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8')
        
        elif format.lower() == 'excel':
            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False)
        
        else:
            raise ValueError(f"Unsupported output format: {format}")
        
        logger.info(f"Data saved to {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving output to {output_path}: {e}")
        return False


def extract_table_from_text(text: str) -> List[List[str]]:
    """Extract table-like structure from text"""
    lines = text.strip().split('\n')
    table = []
    
    for line in lines:
        # Split by common delimiters
        row = re.split(r'\s{2,}|\t|,', line.strip())
        row = [cell.strip() for cell in row if cell.strip()]
        
        if row:
            table.append(row)
    
    return table


def find_table_boundaries(df: pd.DataFrame) -> tuple:
    """Find the boundaries of the actual transaction table"""
    # Look for rows that contain date-like patterns
    date_pattern = re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}')
    
    start_row = 0
    end_row = len(df)
    
    # Find start row (first row with a date)
    for i in range(len(df)):
        row = df.iloc[i]
        row_str = ' '.join(str(cell) for cell in row if pd.notna(cell))
        if date_pattern.search(row_str):
            start_row = i
            break
    
    # Find end row (last row with a date or amount)
    for i in range(len(df) - 1, start_row, -1):
        row_str = ' '.join(str(cell) for cell in df.iloc[i] if pd.notna(cell))
        if date_pattern.search(row_str) or re.search(r'[\d,]+\.?\d*', row_str):
            end_row = i + 1
            break
    
    return start_row, end_row


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare dataframe for processing"""
    # Remove completely empty rows and columns
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    # Clean cell values
    for col in df.columns:
        df[col] = df[col].astype(str).apply(clean_text)
    
    return df 