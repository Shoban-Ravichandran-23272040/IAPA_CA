# Intelligent Invoice Processor

## Overview

The Intelligent Invoice Processor is an advanced OCR and machine learning-based solution for automating accounts payable invoice processing. This application extracts data from invoice PDFs, classifies vendors, validates information, and provides analytics on processing performance.

## Features

- **Advanced OCR Processing**: Uses Tesseract OCR with custom preprocessing for optimal text extraction
- **Intelligent Data Extraction**: ML-based field recognition and parsing
- **Vendor Classification**: Automatically identifies vendors using a machine learning classifier
- **Validation Engine**: Ensures data consistency and flags exceptions
- **User-Friendly Interface**: Intuitive GUI for invoice processing workflow
- **Analytics Dashboard**: Performance metrics and processing insights
- **Export Capabilities**: Export to CSV or JSON for integration with accounting systems

## Installation

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR engine
- Poppler (for PDF processing)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/intelligent-invoice-processor.git
   cd intelligent-invoice-processor
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure paths in `invoice_processor/config.py`:
   - Set the correct path to Tesseract OCR
   - Set the correct path to Poppler

## Usage

### Running the Application

```
python -m invoice_processor.main
```

### Basic Workflow

1. **Select Invoice**: Click "Select Invoice PDF" and choose a PDF invoice file
2. **Process Invoice**: Click "Process Invoice" to extract data using OCR and ML
3. **Review Results**: Check extraction results and confidence scores
4. **Save to Database**: Save processed invoice data to the database
5. **Export Data**: Export to CSV or JSON for integration with accounting systems

### Analytics

Navigate to the Analytics tab to view:
- Vendor distribution
- Processing volume over time
- Performance metrics by status (Auto-Approved, Needs Review, Manual Processing)

## Project Structure

The project follows a modular structure:

- `invoice_processor/`: Main package
  - `core/`: Core functionality (OCR, ML, extraction)
  - `ui/`: User interface components
  - `utils/`: Utility functions
  - `data/`: Data storage and models

## Development

### Running Tests

```
pytest tests/
```

### Adding New Features

The modular architecture makes it easy to extend the application:
- Add new extraction capabilities in `core/data_extractor.py`
- Enhance ML models in `core/ml_classifier.py`
- Add new UI features in the appropriate UI modules

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses Tesseract OCR for text recognition
- Leverages scikit-learn for machine learning components
- Built with tkinter for the user interface