# Intelligent Invoice Processor

## Overview

This repository contains the implementation of an intelligent invoice processing system developed as part of the H9IAPI Intelligent Agents and Process Automation course assignment. The system demonstrates how intelligent automation can transform the traditionally manual accounts payable process using OCR, machine learning, and workflow automation.

## Business Process Context

This implementation addresses the accounts payable invoice processing workflow, which includes:
- Document capture and digitization
- Data extraction
- Vendor identification
- Validation
- Approval routing
- Accounting system integration

The BPMN process model and detailed analysis can be found in the accompanying report.

## Features

- **Advanced OCR Processing**: Uses Tesseract OCR with custom preprocessing for optimal text extraction
- **Machine Learning Classification**: Automatically identifies vendors using a RandomForestClassifier
- **Intelligent Data Extraction**: Pattern recognition and NLP techniques for field extraction
- **Validation Engine**: Multi-level validation with confidence scoring
- **User-Friendly Interface**: Intuitive GUI for invoice processing workflow
- **Analytics Dashboard**: Performance metrics and processing insights
- **Export Capabilities**: Integration with accounting systems

## System Architecture

The system follows a modular architecture:

- `invoice_processor/`: Main package
  - `core/`: Core functionality (OCR, ML, extraction)
    - `document_processor.py`: PDF/image handling and OCR
    - `data_extractor.py`: Field and line item extraction
    - `ml_classifier.py`: Machine learning for vendor classification
    - `database.py`: Storage and retrieval operations
  - `ui/`: User interface components
    - `app.py`: Main application window
    - `process_tab.py`: Invoice processing interface
    - `database_tab.py`: Database management interface
    - `analytics_tab.py`: Performance analytics
  - `utils/`: Utility functions
    - `validation_utils.py`: Data validation
    - `image_utils.py`: Image preprocessing
    - `export_utils.py`: Accounting system integration
  - `data/`: Data storage and models
    - `vendor_database.py`: Vendor information

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR engine
- Poppler (for PDF processing)

### Installation Steps

1. Clone the repository:
   ```
   git clone https://github.com/Shoban-Ravichandran-23272040/IAPA_CA.git
   cd intelligent-invoice-processor
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure paths in `invoice_processor/config.py`:
   - Set the path to Tesseract OCR
   - Set the path to Poppler
   - Adjust other configuration settings as needed

## Usage

### Running the Application

```
python -m invoice_processor.main
```

### Processing Invoices

1. **Select Invoice**: Click "Select Invoice PDF" to choose an invoice file
2. **Process Invoice**: Extract data using OCR and ML
3. **Review Results**: Check extraction results and confidence scores
4. **Save to Database**: Store processed invoice data
5. **Export Data**: Export to accounting systems in various formats

### Analytics

Navigate to the Analytics tab to view:
- Vendor distribution
- Processing volume over time
- Confidence score analysis
- Performance metrics

## Implementation Highlights

### Automated Task 1: Vendor Classification

The system uses machine learning to automatically identify vendors based on invoice content:

```python
# From ml_classifier.py
def predict(self, text):
    """
    Predict vendor from invoice text
    
    Args:
        text (str): Invoice text to classify
        
    Returns:
        tuple: (predicted_vendor, confidence_score)
    """
    try:
        # Vectorize the input text
        X = self.vectorizer.transform([text])
        
        # Get prediction and probability
        prediction = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)[0]
        max_proba = max(proba)
        
        return prediction, max_proba
    except Exception as e:
        # Fall back to fuzzy matching if ML prediction fails
        return self._fuzzy_match_vendor(text)
```

### Automated Task 2: Intelligent Data Extraction

The system extracts invoice fields using pattern recognition and NLP techniques:

```python
# From data_extractor.py
# Extract metadata using regex patterns
patterns = {
    "invoice_no": [r'Invoice\s*(?:#|No|Number|num)[:.\s]*\s*([A-Za-z0-9-]+)'],
    "date": [r'(?:Invoice\s*)?Date[:.\s]*\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})'],
    "total_amount": [r'(?:Total|Amount\s*Due)[:.\s]*\s*\$?\s*(\d+[,\d]*\.\d+)']
}

for field, pattern_list in patterns.items():
    for pattern in pattern_list:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            result["metadata"][field] = value
            break
```

### Automated Task 3: Confidence-Based Workflow Routing

The system automatically routes invoices based on confidence scores:

```python
# From data_extractor.py
# Set status based on confidence and warnings
if overall_confidence >= ML_CONFIDENCE_THRESHOLD and not result["validation"]["warnings"]:
    result["validation"]["status"] = "Auto-Approved"
elif overall_confidence >= 0.6:
    result["validation"]["status"] = "Needs Review"
else:
    result["validation"]["status"] = "Manual Processing Required"
```

## Results & Performance

The system demonstrates significant improvements over manual processing:

- **Processing Speed**: Reduces invoice processing from minutes to seconds
- **Accuracy**: Consistently extracts data from standard invoice formats
- **Automation Rate**: Approximately 75-80% of the process can be automated
- **Confidence Scoring**: Provides transparent metrics on extraction reliability

## Future Enhancements

- **Deep Learning OCR**: Replace Tesseract with domain-specific models
- **Adaptive Document Understanding**: Self-learning templates for new vendors
- **Fraud Detection**: AI-based anomaly detection for suspicious invoices
- **Natural Language Interfaces**: Conversational AI for invoice management
- **Mobile Capabilities**: Extend to mobile device capture and processing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Uses Tesseract OCR for text recognition
- Leverages scikit-learn for machine learning components
- Built with tkinter for the user interface
