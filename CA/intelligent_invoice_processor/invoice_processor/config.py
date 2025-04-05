"""
Configuration settings for the Invoice Processor application.
Update these settings according to your environment.
"""

import os
import platform
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "invoice_processor" / "data"
MODELS_DIR = DATA_DIR / "models"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# File paths
DATABASE_PATH = DATA_DIR / "invoice_database.csv"
MODEL_PATH = MODELS_DIR / "vendor_classifier.pkl"

# OCR Configuration
# Default paths, will be overridden by environment-specific settings below
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPPLER_PATH = r'C:\Program Files\poppler-24.08.0\Library\bin'

# Environment-specific configurations
if platform.system() == 'Windows':
    # Windows paths
    TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    POPPLER_PATH = r'C:\Program Files\poppler-24.08.0\Library\bin'
elif platform.system() == 'Linux':
    # Linux paths
    TESSERACT_PATH = '/usr/bin/tesseract'
    POPPLER_PATH = '/usr/bin'
elif platform.system() == 'Darwin':
    # Mac OS paths
    TESSERACT_PATH = '/usr/local/bin/tesseract'
    POPPLER_PATH = '/usr/local/bin'

# Override with environment variables if set
if os.environ.get('TESSERACT_PATH'):
    TESSERACT_PATH = os.environ.get('TESSERACT_PATH')
if os.environ.get('POPPLER_PATH'):
    POPPLER_PATH = os.environ.get('POPPLER_PATH')

# OCR Configuration
OCR_DPI = 300  # DPI for PDF to image conversion
OCR_LANG = 'eng'  # OCR language
OCR_CONFIG = '--psm 6 --oem 3'  # OCR configuration

# Machine Learning Configuration
ML_CONFIDENCE_THRESHOLD = 0.8  # Threshold for auto-approval
ML_TRAIN_SAMPLES_PER_VENDOR = 10  # Number of training samples per vendor

# UI Configuration
UI_WINDOW_SIZE = "900x700"
UI_TITLE = "Intelligent Invoice Processor"