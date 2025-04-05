"""
Document processing module for invoice OCR.

This module handles PDF to image conversion, image preprocessing,
and OCR text extraction.
"""

import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
import os

from invoice_processor.config import TESSERACT_PATH, POPPLER_PATH, OCR_DPI, OCR_LANG, OCR_CONFIG
from invoice_processor.logger import app_logger

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def preprocess_image(image):
    """
    Apply image preprocessing techniques to improve OCR quality
    
    Args:
        image (PIL.Image): Input image
        
    Returns:
        PIL.Image: Preprocessed image
    """
    app_logger.debug("Preprocessing image")
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Convert back to PIL Image
        return Image.fromarray(opening)
    except Exception as e:
        app_logger.error(f"Error in image preprocessing: {str(e)}")
        # Return original image if preprocessing fails
        return image

def extract_text_from_invoice(pdf_path):
    """
    Extract text from invoice PDF with improved preprocessing
    
    Args:
        pdf_path (str): Path to the invoice PDF file
        
    Returns:
        dict: Dictionary containing extracted text, original images, and preprocessed images
    """
    app_logger.info(f"Extracting text from PDF: {pdf_path}")
    try:
        # Convert PDF to high-quality images
        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH,
            dpi=300
        )
        
        if not images:
            print("Warning: No images extracted from PDF")
            return {'text': "", 'images': [], 'preprocessed_images': []}
        
        extracted_text = ""
        preprocessed_images = []
        
        for img in images:
            try:
                # Apply preprocessing
                processed_img = preprocess_image(img)
                preprocessed_images.append(processed_img)
                
                # Perform OCR with improved configuration
                text = pytesseract.image_to_string(
                    processed_img,
                    lang='eng',
                    config='--psm 6 --oem 3'
                )
                
                # Clean up extracted text to avoid JSON parsing issues
                text = text.replace('"', '"').replace('"', '"')  # Normalize quotes
                text = ''.join(c if ord(c) < 128 else ' ' for c in text)  # Remove non-ASCII chars
                
                extracted_text += text
            except Exception as e:
                print(f"Error processing an image: {str(e)}")
                continue
        
        return {
            'text': extracted_text,
            'images': images,
            'preprocessed_images': preprocessed_images
        }
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'text': "", 'images': [], 'preprocessed_images': []}

def preview_invoice(pdf_path, page=1, dpi=150):
    """
    Create a preview image of a specific page in the invoice
    
    Args:
        pdf_path (str): Path to the invoice PDF file
        page (int): Page number to preview (1-based)
        dpi (int): Resolution for the preview image
        
    Returns:
        PIL.Image: Preview image or None if failed
    """
    app_logger.debug(f"Generating preview for {pdf_path}, page {page}")
    try:
        # Convert first page of PDF to image
        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH,
            first_page=page,
            last_page=page,
            dpi=dpi
        )
        
        if images:
            return images[0]
        return None
    except Exception as e:
        app_logger.error(f"Error creating preview: {str(e)}")
        return None