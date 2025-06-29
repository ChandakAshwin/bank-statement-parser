"""
OCR Processor for scanned PDF documents
"""

import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
import os

from config import OCR_CONFIG
from utils import clean_text

logger = logging.getLogger(__name__)

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OCRProcessor:
    """Handles OCR processing for scanned PDF documents"""
    
    def __init__(self):
        self.config = OCR_CONFIG
        self._check_tesseract_installation()
    
    def _check_tesseract_installation(self):
        """Check if Tesseract is properly installed"""
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR is available")
        except Exception as e:
            logger.error(f"Tesseract OCR not found: {e}")
            logger.error("Please install Tesseract OCR:")
            logger.error("Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            logger.error("macOS: brew install tesseract")
            logger.error("Linux: sudo apt-get install tesseract-ocr")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply noise reduction
        denoised = cv2.medianBlur(gray, 3)
        
        # Apply thresholding to get binary image
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from a single image"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not read image: {image_path}")
                return ""
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Perform OCR
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.config['language'],
                config=self.config['config']
            )
            
            return clean_text(text)
        
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            return ""
    
    def extract_text_from_pdf_images(self, image_paths: List[str]) -> str:
        """Extract text from multiple PDF page images"""
        all_text = []
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"Processing page {i+1}/{len(image_paths)}")
            
            page_text = self.extract_text_from_image(image_path)
            if page_text:
                all_text.append(page_text)
        
        return "\n\n".join(all_text)
    
    def extract_tables_from_image(self, image_path: str) -> List[List[List[str]]]:
        """Extract tables from image using OCR"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return []
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract table data using Tesseract
            table_data = pytesseract.image_to_data(
                processed_image,
                lang=self.config['language'],
                config=self.config['config'],
                output_type=pytesseract.Output.DICT
            )
            
            # Process the data to extract table structure
            tables = self._process_table_data(table_data)
            
            return tables
        
        except Exception as e:
            logger.error(f"Error extracting tables from image {image_path}: {e}")
            return []
    
    def _process_table_data(self, table_data: dict) -> List[List[List[str]]]:
        """Process OCR table data into structured tables"""
        tables = []
        current_table = []
        current_row = []
        last_y = -1
        last_x = -1
        
        # Sort by y coordinate (rows) then x coordinate (columns)
        sorted_data = sorted(
            zip(table_data['text'], table_data['left'], table_data['top'], table_data['conf']),
            key=lambda x: (x[2], x[1])  # Sort by top, then left
        )
        
        for text, x, y, conf in sorted_data:
            # Skip low confidence results and empty text
            if conf < 30 or not text.strip():
                continue
            
            text = clean_text(text)
            if not text:
                continue
            
            # Check if this is a new row (significant y difference)
            if last_y != -1 and abs(y - last_y) > 20:
                if current_row:
                    current_table.append(current_row)
                    current_row = []
            
            # Check if this is a new table (significant x difference or new page)
            if last_x != -1 and abs(x - last_x) > 200:
                if current_table:
                    tables.append(current_table)
                    current_table = []
            
            current_row.append(text)
            last_x = x
            last_y = y
        
        # Add remaining row and table
        if current_row:
            current_table.append(current_row)
        if current_table:
            tables.append(current_table)
        
        return tables
    
    def detect_table_regions(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """Detect table regions in image using contour detection"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return []
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            table_regions = []
            
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size (tables should be reasonably large)
                if w > 100 and h > 50:
                    table_regions.append((x, y, w, h))
            
            return table_regions
        
        except Exception as e:
            logger.error(f"Error detecting table regions in {image_path}: {e}")
            return []
    
    def enhance_image_quality(self, image_path: str, output_path: Optional[str] = None) -> str:
        """Enhance image quality for better OCR results"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return image_path
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(enhanced)
            
            # Apply sharpening
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # Save enhanced image
            if output_path is None:
                output_path = image_path.replace('.png', '_enhanced.png')
            
            cv2.imwrite(output_path, sharpened)
            logger.info(f"Enhanced image saved to: {output_path}")
            
            return output_path
        
        except Exception as e:
            logger.error(f"Error enhancing image {image_path}: {e}")
            return image_path
    
    def extract_text_with_layout(self, image_path: str) -> dict:
        """Extract text with layout information"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return {}
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text with bounding boxes
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.config['language'],
                config=self.config['config'],
                output_type=pytesseract.Output.DICT
            )
            
            # Process layout information
            layout_info = {
                'text_blocks': [],
                'tables': [],
                'headers': [],
                'footers': []
            }
            
            height, width = processed_image.shape
            
            for i in range(len(data['text'])):
                if data['conf'][i] > 30 and data['text'][i].strip():
                    text = clean_text(data['text'][i])
                    if text:
                        block = {
                            'text': text,
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'confidence': data['conf'][i]
                        }
                        
                        # Categorize based on position
                        if block['y'] < height * 0.1:  # Top 10%
                            layout_info['headers'].append(block)
                        elif block['y'] > height * 0.9:  # Bottom 10%
                            layout_info['footers'].append(block)
                        else:
                            layout_info['text_blocks'].append(block)
            
            return layout_info
        
        except Exception as e:
            logger.error(f"Error extracting text with layout from {image_path}: {e}")
            return {}
    
    def is_scanned_document(self, image_path: str) -> bool:
        """Determine if an image is from a scanned document"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return False
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate text density (ratio of text pixels to total pixels)
            # This is a simple heuristic - scanned documents typically have more text
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text_pixels = np.sum(binary == 0)  # Black pixels (text)
            total_pixels = binary.size
            
            text_density = text_pixels / total_pixels
            
            # Scanned documents typically have higher text density
            return text_density > 0.1
        
        except Exception as e:
            logger.error(f"Error determining if document is scanned: {e}")
            return True  # Assume scanned if we can't determine 