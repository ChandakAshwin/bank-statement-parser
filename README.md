# Bank Statement Parser AI Agent

An intelligent AI agent that can parse bank statements from various banks and extract structured transaction data from PDF and Excel files.

## Features

- **Multi-format Support**: Handles both PDF (native and scanned) and Excel files
- **Intelligent Parsing**: Automatically detects and maps columns regardless of bank format
- **OCR Capability**: Extracts text from scanned PDF documents
- **Structured Output**: Returns clean, standardized transaction data
- **Web Interface**: User-friendly Streamlit web app for easy file upload and processing
- **Error Handling**: Robust error handling for various edge cases

## Extracted Data Fields

- **Transaction Date**: Parsed and standardized date format
- **Description/Merchant**: Transaction description or merchant name
- **Amount**: Transaction amount (positive for credits, negative for debits)
- **Debit/Credit**: Transaction type classification
- **Closing Balance**: Account balance after transaction
- **Category** (Optional): Expense categorization

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Tesseract OCR (required for scanned PDF processing):
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

## Usage

### Web Interface (Recommended)
```bash
streamlit run app.py
```
Then open your browser to the provided URL and upload your bank statement files.

### Command Line Interface
```bash
python main.py --file path/to/statement.pdf
```

### Python API
```python
from bank_parser import BankStatementParser

parser = BankStatementParser()
transactions = parser.parse_file("path/to/statement.pdf")
print(transactions)
```

## Supported File Types

- **PDF Files**: Native PDFs with text and scanned/image-based PDFs
- **Excel Files**: .xls and .xlsx formats
- **Multi-page Documents**: Automatically processes all pages

## Project Structure

```
Bank Statement/
├── main.py                 # Main entry point
├── app.py                  # Streamlit web interface
├── bank_parser.py          # Core parsing logic
├── pdf_processor.py        # PDF-specific processing
├── excel_processor.py      # Excel-specific processing
├── ocr_processor.py        # OCR and image processing
├── data_extractor.py       # Data extraction and normalization
├── utils.py               # Utility functions
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Example Output

```json
[
  {
    "date": "2024-01-15",
    "description": "WALMART SUPERCENTER",
    "amount": -125.50,
    "debit_credit": "debit",
    "balance": 1542.75,
    "category": "shopping"
  },
  {
    "date": "2024-01-16",
    "description": "SALARY DEPOSIT",
    "amount": 2500.00,
    "debit_credit": "credit",
    "balance": 4042.75,
    "category": "income"
  }
]
```

## Error Handling

The agent handles various edge cases:
- Unsupported file formats
- Corrupted or unreadable files
- Missing or ambiguous column headers
- Inconsistent date formats
- OCR failures

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License 