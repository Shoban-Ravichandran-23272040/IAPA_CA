"""
Core functionality for invoice processing.

This package contains the main processing components:
- Document processing and OCR
- Data extraction and validation
- Machine learning classification
- Database operations
"""

from invoice_processor.core.document_processor import extract_text_from_invoice, preprocess_image
from invoice_processor.core.data_extractor import parse_invoice_text
from invoice_processor.core.ml_classifier import VendorClassifier
from invoice_processor.core.database import save_to_database, export_to_accounting_system