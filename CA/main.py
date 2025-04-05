import pytesseract
from pdf2image import convert_from_path
import re
import os
import pandas as pd
import numpy as np
import json
import datetime
from fuzzywuzzy import process
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
import pickle
import cv2
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

# Configure paths
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPPLER_PATH = r'C:\Program Files\poppler-24.08.0\Library\bin'
MODEL_PATH = 'vendor_classifier.pkl'
DATABASE_PATH = 'invoice_database.csv'

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Predefined vendor information for matching and validation
VENDOR_DATABASE = {
    "ABC Supplies Ltd.": {
        "address": "123 Supply St, Business Park",
        "tax_id": "AB123456789",
        "payment_terms": "Net 30",
        "typical_items": ["paper", "toner", "pens", "staples"]
    },
    "XYZ Traders Inc.": {
        "address": "456 Trading Ave, Commerce City",
        "tax_id": "XY987654321",
        "payment_terms": "Net 15",
        "typical_items": ["mouse", "keyboard", "monitor", "laptop"]
    },
    "Global Tech Solutions": {
        "address": "789 Tech Blvd, Innovation District",
        "tax_id": "GT567891234",
        "payment_terms": "Net 45",
        "typical_items": ["software license", "cloud storage", "support hours", "consulting"]
    },
    "Fast Retail Corp.": {
        "address": "321 Retail Row, Shopping Center",
        "tax_id": "FR654321987",
        "payment_terms": "2/10 Net 30",
        "typical_items": ["furniture", "office supplies", "cleaning supplies", "break room items"]
    }
}

# Create or verify database file exists
def initialize_database():
    if not os.path.exists(DATABASE_PATH):
        # Create empty dataframe with necessary columns
        columns = ['invoice_id', 'vendor', 'date', 'amount', 'status', 
                   'processed_date', 'json_data', 'confidence_score']
        df = pd.DataFrame(columns=columns)
        df.to_csv(DATABASE_PATH, index=False)
        print(f"Created new database at {DATABASE_PATH}")
    else:
        print(f"Using existing database at {DATABASE_PATH}")

# Image preprocessing to improve OCR quality
def preprocess_image(image):
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

# Function to extract text from invoice PDF with improved preprocessing
def extract_text_from_invoice(pdf_path):
    try:
        # Convert PDF to high-quality images
        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH,
            dpi=300  # Higher DPI for better quality
        )
        
        extracted_text = ""
        preprocessed_images = []
        
        for img in images:
            # Apply preprocessing
            processed_img = preprocess_image(img)
            preprocessed_images.append(processed_img)
            
            # Perform OCR with improved configuration
            extracted_text += pytesseract.image_to_string(
                processed_img,
                lang='eng',
                config='--psm 6 --oem 3 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:/\\-$ "'
            )
        
        return {
            'text': extracted_text,
            'images': images,
            'preprocessed_images': preprocessed_images
        }
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
        return {'text': "", 'images': [], 'preprocessed_images': []}

# Machine learning model for vendor classification
class VendorClassifier:
    def __init__(self):
        self.vectorizer = CountVectorizer(analyzer='word', ngram_range=(1, 2))
        self.model = RandomForestClassifier(n_estimators=100)
        self.classes = list(VENDOR_DATABASE.keys())
        
    def train(self, training_data):
        # Training data should be list of (text, vendor_name) tuples
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        # Vectorize the text
        X = self.vectorizer.fit_transform(texts)
        
        # Train the model
        self.model.fit(X, labels)
    
    def predict(self, text):
        # Vectorize the input text
        X = self.vectorizer.transform([text])
        
        # Get prediction and probability
        prediction = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)[0]
        max_proba = max(proba)
        
        return prediction, max_proba
    
    def save_model(self, path):
        with open(path, 'wb') as f:
            pickle.dump((self.vectorizer, self.model, self.classes), f)
    
    def load_model(self, path):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                self.vectorizer, self.model, self.classes = pickle.load(f)
            return True
        return False

# Enhanced function to parse invoice text with validation and confidence scores
def parse_invoice_text(text, vendor_classifier=None):
    # Use ML model if available, otherwise fall back to fuzzy matching
    if vendor_classifier:
        vendor, confidence = vendor_classifier.predict(text[:500])  # Use first 500 chars for classification
    else:
        # Fuzzy match vendor name from the first few lines
        first_lines = '\n'.join(text.split('\n')[:5])
        vendor_match = process.extractOne(first_lines, list(VENDOR_DATABASE.keys()))
        vendor = vendor_match[0]
        confidence = vendor_match[1] / 100.0  # Convert to 0-1 scale
    
    # Dictionary to store all extracted data and confidence scores
    result = {
        "vendor": {
            "name": vendor,
            "confidence": confidence
        },
        "metadata": {},
        "items": [],
        "totals": {},
        "validation": {
            "overall_confidence": 0,
            "warnings": [],
            "status": "Pending Review"
        }
    }
    
    # More sophisticated regex patterns for various invoice fields
    patterns = {
        "invoice_no": [r'Invoice\s*(?:#|No|Number|num)[:.\s]*\s*([A-Za-z0-9-]+)', 
                     r'Invoice\s*ID[:.\s]*\s*([A-Za-z0-9-]+)'],
        "date": [r'(?:Invoice\s*)?Date[:.\s]*\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
                r'(?:Invoice\s*)?Date[:.\s]*\s*(\d{1,2}\s+[A-Za-z]+\s+\d{2,4})'],
        "due_date": [r'Due\s*Date[:.\s]*\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
                    r'Payment\s*Due[:.\s]*\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})'],
        "po_number": [r'P\.?O\.?\s*(?:Number|No|#)?[:.\s]*\s*([A-Za-z0-9-]+)',
                     r'Purchase\s*Order\s*(?:Number|No|#)?[:.\s]*\s*([A-Za-z0-9-]+)'],
        "total_amount": [r'(?:Total|Amount\s*Due|Balance\s*Due)[:.\s]*\s*\$?\s*(\d+[,\d]*\.\d+)',
                       r'(?:Total|Amount\s*Due|Balance\s*Due)[:.\s]*\s*\$?\s*(\d+[,\d]*)']
    }
    
    # Extract metadata using the patterns
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field == "total_amount":
                    value = value.replace(',', '')
                    try:
                        value = float(value)
                    except ValueError:
                        result["validation"]["warnings"].append(f"Could not convert total amount: {value}")
                        value = 0.0
                result["metadata"][field] = value
                break
    
    # Extract itemized section with improved pattern matching
    try:
        # Look for table headers
        header_patterns = [
            r'(Item|Description|Product)[\s\t]+(Qty|Quantity)[\s\t]+(Price|Rate|Unit\s*Price)[\s\t]+(Amount|Total)',
            r'(Description|Item|Product)[\s\t]+(Quantity|Qty)[\s\t]+(Unit\s*Price|Price|Rate)[\s\t]+(Line\s*Total|Total|Amount)'
        ]
        
        start_line = -1
        end_line = -1
        lines = text.split('\n')
        
        # Find the start of the item table
        for i, line in enumerate(lines):
            for pattern in header_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    start_line = i + 1  # Skip the header line
                    break
            if start_line >= 0:
                break
        
        # If we found a header, try to extract items
        if start_line >= 0:
            # Find the end of the table (typically above the subtotal/total section)
            for i in range(start_line + 1, len(lines)):
                if re.search(r'(Sub)?Total|Tax|Discount|Balance', lines[i], re.IGNORECASE):
                    end_line = i
                    break
            
            # If no end marker found, use a reasonable number of lines
            if end_line < 0:
                end_line = min(start_line + 15, len(lines))
            
            # Extract items
            for i in range(start_line, end_line):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Try various item line formats
                patterns = [
                    r'([A-Za-z0-9\s\-]+)[\s\t]+(\d+)[\s\t]+([\d.,]+)[\s\t]+([\d.,]+)',  # Standard format
                    r'([A-Za-z0-9\s\-]+)[\s\t]+(\d+)[\s\t]+\$([\d.,]+)[\s\t]+\$([\d.,]+)'  # With currency symbols
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        item, qty, price, total = match.groups()
                        result["items"].append({
                            "description": item.strip(),
                            "quantity": int(qty),
                            "unit_price": float(price.replace(',', '')),
                            "total": float(total.replace(',', ''))
                        })
                        break
        
        # Extract total section information
        total_section_patterns = {
            "subtotal": r'Sub[\s\-]?total[:.\s]*\s*\$?\s*([\d.,]+)',
            "tax": r'(?:Tax|VAT|GST)[:.\s]*\s*\$?\s*([\d.,]+)',
            "shipping": r'(?:Shipping|Freight|Delivery)[:.\s]*\s*\$?\s*([\d.,]+)',
            "discount": r'Discount[:.\s]*\s*\$?\s*([\d.,]+)',
            "total": r'(?:Total|Balance\s*Due)[:.\s]*\s*\$?\s*([\d.,]+)'
        }
        
        for field, pattern in total_section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    result["totals"][field] = value
                except ValueError:
                    result["validation"]["warnings"].append(f"Could not convert {field}: {match.group(1)}")
    
    except Exception as e:
        result["validation"]["warnings"].append(f"Error extracting items: {str(e)}")
    
    # Validation steps
    validation_score = 0
    
    # 1. Check if we have the essential fields
    essential_fields = ["invoice_no", "date", "total_amount"]
    for field in essential_fields:
        if field in result["metadata"]:
            validation_score += 1
    
    # 2. Verify items total matches the invoice total if both are available
    if result["items"] and "total" in result["totals"]:
        items_total = sum(item["total"] for item in result["items"])
        invoice_total = result["totals"]["total"]
        
        # Allow for small rounding differences
        if abs(items_total - invoice_total) <= 0.02:
            validation_score += 1
        else:
            result["validation"]["warnings"].append(
                f"Item total ({items_total}) doesn't match invoice total ({invoice_total})"
            )
    
    # 3. Check for invoice date validity
    if "date" in result["metadata"]:
        try:
            # Try multiple date formats
            date_formats = ["%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%m.%d.%Y", "%d.%m.%Y"]
            date_str = result["metadata"]["date"]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                # Check if date is reasonable (not in the future, not too old)
                today = datetime.datetime.now()
                if parsed_date <= today and parsed_date >= today - datetime.timedelta(days=365):
                    validation_score += 1
                else:
                    result["validation"]["warnings"].append(f"Invoice date {date_str} seems unusual")
            else:
                result["validation"]["warnings"].append(f"Couldn't parse date: {date_str}")
        except Exception as e:
            result["validation"]["warnings"].append(f"Date validation error: {str(e)}")
    
    # Calculate overall confidence score
    max_score = 3 + (1 if result["items"] else 0)  # Maximum possible validation score
    if max_score > 0:
        overall_confidence = (validation_score / max_score) * confidence
    else:
        overall_confidence = confidence * 0.5
    
    result["validation"]["overall_confidence"] = overall_confidence
    
    # Set status based on confidence and warnings
    if overall_confidence >= 0.8 and not result["validation"]["warnings"]:
        result["validation"]["status"] = "Auto-Approved"
    elif overall_confidence >= 0.6:
        result["validation"]["status"] = "Needs Review"
    else:
        result["validation"]["status"] = "Manual Processing Required"
    
    return result

# Function to save processed invoice to database
def save_to_database(invoice_data, pdf_path):
    try:
        # Read existing database
        df = pd.read_csv(DATABASE_PATH)
        
        # Create new record
        new_record = {
            'invoice_id': invoice_data['metadata'].get('invoice_no', 'Unknown'),
            'vendor': invoice_data['vendor']['name'],
            'date': invoice_data['metadata'].get('date', 'Unknown'),
            'amount': invoice_data['metadata'].get('total_amount', 
                     invoice_data['totals'].get('total', 0)),
            'status': invoice_data['validation']['status'],
            'processed_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'json_data': json.dumps(invoice_data),
            'confidence_score': invoice_data['validation']['overall_confidence']
        }
        
        # Append to dataframe
        df = df.append(new_record, ignore_index=True)
        
        # Save back to CSV
        df.to_csv(DATABASE_PATH, index=False)
        
        return True
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        return False

# Function to export processed data to accounting system format
def export_to_accounting_system(invoice_data, output_format="csv"):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
        
        if output_format.lower() == "csv":
            filename = f"export_{invoice_id}_{timestamp}.csv"
            
            # Create export data structure
            export_data = {
                'InvoiceNumber': [invoice_data['metadata'].get('invoice_no', '')],
                'Vendor': [invoice_data['vendor']['name']],
                'Date': [invoice_data['metadata'].get('date', '')],
                'DueDate': [invoice_data['metadata'].get('due_date', '')],
                'PONumber': [invoice_data['metadata'].get('po_number', '')],
                'TotalAmount': [invoice_data['metadata'].get('total_amount', 
                               invoice_data['totals'].get('total', 0))],
                'Status': [invoice_data['validation']['status']],
                'ConfidenceScore': [invoice_data['validation']['overall_confidence']]
            }
            
            # Add line items if available
            if invoice_data['items']:
                # Separate CSV for line items
                items_filename = f"export_{invoice_id}_items_{timestamp}.csv"
                items_data = {
                    'InvoiceNumber': [],
                    'Description': [],
                    'Quantity': [],
                    'UnitPrice': [],
                    'TotalPrice': []
                }
                
                for item in invoice_data['items']:
                    items_data['InvoiceNumber'].append(invoice_data['metadata'].get('invoice_no', ''))
                    items_data['Description'].append(item['description'])
                    items_data['Quantity'].append(item['quantity'])
                    items_data['UnitPrice'].append(item['unit_price'])
                    items_data['TotalPrice'].append(item['total'])
                
                pd.DataFrame(items_data).to_csv(items_filename, index=False)
                print(f"Item data exported to {items_filename}")
            
            # Save main invoice data
            pd.DataFrame(export_data).to_csv(filename, index=False)
            print(f"Invoice data exported to {filename}")
            
            return filename
        
        elif output_format.lower() == "json":
            filename = f"export_{invoice_id}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(invoice_data, f, indent=2)
            print(f"Invoice data exported to {filename}")
            return filename
        
        else:
            print(f"Unsupported output format: {output_format}")
            return None
            
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        return None

# Training data generator for the model
def generate_training_data():
    training_data = []
    
    # Generate training examples for each vendor
    for vendor_name, vendor_info in VENDOR_DATABASE.items():
        # Basic invoice template with vendor information
        template = f"""
        {vendor_name}
        {vendor_info['address']}
        Tax ID: {vendor_info['tax_id']}
        
        INVOICE
        
        Invoice No: INV-{vendor_name[:3].upper()}-12345
        Date: 03/15/2024
        Due Date: 04/15/2024
        PO Number: PO-2024-001
        
        Payment Terms: {vendor_info['payment_terms']}
        """
        
        # Add some variations of this template
        for i in range(10):
            # Slightly modify the text each time
            variation = template.replace("INV-", f"INV{i}-")
            variation = variation.replace("03/15/2024", f"03/{15+i}/2024")
            variation = variation.replace("PO-2024-001", f"PO-2024-{1000+i}")
            
            # Add some random items from this vendor's typical items
            import random
            items_section = "\nItems:\n"
            for _ in range(random.randint(1, 4)):
                item = random.choice(vendor_info['typical_items'])
                qty = random.randint(1, 10)
                price = round(random.uniform(10, 200), 2)
                total = qty * price
                items_section += f"{item} {qty} ${price:.2f} ${total:.2f}\n"
            
            variation += items_section
            
            # Add to training data
            training_data.append((variation, vendor_name))
    
    return training_data

# Simple GUI for demonstration
class InvoiceProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Intelligent Invoice Processor")
        self.root.geometry("900x700")
        
        # Initialize vendor classifier
        self.vendor_classifier = VendorClassifier()
        
        # Try to load existing model, or train a new one
        if not self.vendor_classifier.load_model(MODEL_PATH):
            print("Training new vendor classification model...")
            training_data = generate_training_data()
            self.vendor_classifier.train(training_data)
            self.vendor_classifier.save_model(MODEL_PATH)
        
        # Initialize database
        initialize_database()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.tab_control = ttk.Notebook(self.main_frame)
        
        self.process_tab = ttk.Frame(self.tab_control)
        self.data_tab = ttk.Frame(self.tab_control)
        self.analytics_tab = ttk.Frame(self.tab_control)
        
        self.tab_control.add(self.process_tab, text="Process Invoice")
        self.tab_control.add(self.data_tab, text="Invoice Database")
        self.tab_control.add(self.analytics_tab, text="Analytics")
        self.tab_control.pack(expand=True, fill=tk.BOTH)
        
        # Set up the processing tab
        self.setup_process_tab()
        
        # Set up the database tab
        self.setup_data_tab()
        
        # Set up the analytics tab
        self.setup_analytics_tab()
        
        # Variables for storing current invoice data
        self.current_pdf_path = None
        self.current_extraction_result = None
        self.current_invoice_data = None
        self.current_images = []
    
    def setup_process_tab(self):
        # Create frames
        top_frame = ttk.Frame(self.process_tab, padding=10)
        top_frame.pack(fill=tk.X)
        
        middle_frame = ttk.Frame(self.process_tab, padding=10)
        middle_frame.pack(fill=tk.BOTH, expand=True)
        
        bottom_frame = ttk.Frame(self.process_tab, padding=10)
        bottom_frame.pack(fill=tk.X)
        
        # Top frame controls
        ttk.Label(top_frame, text="Invoice Processing", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="Select Invoice PDF", command=self.select_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Process Invoice", command=self.process_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Save to Database", command=self.save_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Export Data", command=self.export_data).pack(side=tk.LEFT, padx=5)
        
        # Middle frame - split into image preview and data display
        left_frame = ttk.Frame(middle_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(middle_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Image preview area
        ttk.Label(left_frame, text="Document Preview", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        self.image_frame = ttk.Frame(left_frame, borderwidth=1, relief=tk.SUNKEN)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Extracted data display
        ttk.Label(right_frame, text="Extracted Data", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # Create a frame for the results
        result_frame = ttk.Frame(right_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results display using a Text widget with scrollbar
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, width=40, height=20)
        result_scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom frame status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready to process invoices")
        status_bar = ttk.Label(bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X)
        
        # Confidence meter
        self.confidence_frame = ttk.Frame(bottom_frame)
        self.confidence_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.confidence_frame, text="Confidence:").pack(side=tk.LEFT, padx=5)
        self.confidence_var = tk.DoubleVar()
        self.confidence_var.set(0.0)
        self.confidence_meter = ttk.Progressbar(self.confidence_frame, variable=self.confidence_var, 
                                               maximum=100, length=200, mode='determinate')
        self.confidence_meter.pack(side=tk.LEFT, padx=5)
        
        self.confidence_label = ttk.Label(self.confidence_frame, text="0%")
        self.confidence_label.pack(side=tk.LEFT, padx=5)
    
    def setup_data_tab(self):
        # Create a frame for the database controls
        control_frame = ttk.Frame(self.data_tab, padding=10)
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Invoice Database", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Refresh Data", command=self.load_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="View Selected Invoice", command=self.view_invoice).pack(side=tk.LEFT, padx=5)
        
        # Create a frame for the database table
        table_frame = ttk.Frame(self.data_tab, padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Database table
        columns = ('invoice_id', 'vendor', 'date', 'amount', 'status', 'confidence')
        self.invoice_table = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Define headings
        self.invoice_table.heading('invoice_id', text='Invoice #')
        self.invoice_table.heading('vendor', text='Vendor')
        self.invoice_table.heading('date', text='Date')
        self.invoice_table.heading('amount', text='Amount')
        self.invoice_table.heading('status', text='Status')
        self.invoice_table.heading('confidence', text='Confidence')
        
        # Define columns
        self.invoice_table.column('invoice_id', width=100)
        self.invoice_table.column('vendor', width=150)
        self.invoice_table.column('date', width=100)
        self.invoice_table.column('amount', width=100)
        self.invoice_table.column('status', width=150)
        self.invoice_table.column('confidence', width=100)
        
        # Add a scrollbar
        table_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.invoice_table.yview)
        self.invoice_table.configure(yscrollcommand=table_scrollbar.set)
        
        # Pack the table and scrollbar
        self.invoice_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load the database
        self.load_database()
    
    def setup_analytics_tab(self):
        # Create frames for analytics content
        top_frame = ttk.Frame(self.analytics_tab, padding=10)
        top_frame.pack(fill=tk.X)
        
        content_frame = ttk.Frame(self.analytics_tab, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Analytics title and controls
        ttk.Label(top_frame, text="Invoice Analytics", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Generate Reports", command=self.generate_analytics).pack(side=tk.LEFT, padx=5)
        
        # Create notebook for different analytics views
        analytics_notebook = ttk.Notebook(content_frame)
        
        # Create tabs for different analytics
        vendor_tab = ttk.Frame(analytics_notebook)
        time_tab = ttk.Frame(analytics_notebook)
        performance_tab = ttk.Frame(analytics_notebook)
        
        analytics_notebook.add(vendor_tab, text="Vendor Analysis")
        analytics_notebook.add(time_tab, text="Time Analysis")
        analytics_notebook.add(performance_tab, text="Performance Metrics")
        
        analytics_notebook.pack(expand=True, fill=tk.BOTH)
        
        # Vendor Analysis Tab
        vendor_frame = ttk.Frame(vendor_tab, padding=10)
        vendor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for the vendor chart
        self.vendor_canvas = tk.Canvas(vendor_frame, bg="white")
        self.vendor_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Time Analysis Tab
        time_frame = ttk.Frame(time_tab, padding=10)
        time_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for the time chart
        self.time_canvas = tk.Canvas(time_frame, bg="white")
        self.time_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Performance Metrics Tab
        perf_frame = ttk.Frame(performance_tab, padding=10)
        perf_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for the performance metrics
        self.performance_canvas = tk.Canvas(perf_frame, bg="white")
        self.performance_canvas.pack(fill=tk.BOTH, expand=True)
        
    def select_invoice(self):
        """Open file dialog to select an invoice PDF"""
        filetypes = (("PDF files", "*.pdf"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(
            title="Select Invoice PDF",
            filetypes=filetypes
        )
        
        if filepath:
            self.current_pdf_path = filepath
            self.status_var.set(f"Selected: {os.path.basename(filepath)}")
            
            # Clear previous results
            self.result_text.delete(1.0, tk.END)
            self.current_extraction_result = None
            self.current_invoice_data = None
            
            # Show first page preview
            self.preview_invoice(filepath)
    
    def preview_invoice(self, pdf_path):
        """Display a preview of the first page of the PDF"""
        try:
            # Convert first page of PDF to image
            images = convert_from_path(
                pdf_path,
                poppler_path=POPPLER_PATH,
                first_page=1,
                last_page=1,
                dpi=150
            )
            
            if images:
                # Resize to fit the display area
                img = images[0]
                img.thumbnail((400, 550))
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Update image label
                self.image_label.config(image=photo)
                self.image_label.image = photo  # Keep a reference to prevent garbage collection
        
        except Exception as e:
            self.status_var.set(f"Error previewing PDF: {str(e)}")
    
    def process_invoice(self):
        """Process the selected invoice PDF"""
        if not self.current_pdf_path:
            self.status_var.set("No invoice selected. Please select an invoice PDF first.")
            return
        
        self.status_var.set("Processing invoice... Please wait.")
        self.root.update()  # Update the UI
        
        try:
            # Extract text from the invoice
            self.current_extraction_result = extract_text_from_invoice(self.current_pdf_path)
            self.current_images = self.current_extraction_result['images']
            
            # Parse the extracted text
            text = self.current_extraction_result['text']
            self.current_invoice_data = parse_invoice_text(text, self.vendor_classifier)
            
            # Update the result display
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, json.dumps(self.current_invoice_data, indent=2))
            
            # Update confidence meter
            confidence = self.current_invoice_data['validation']['overall_confidence'] * 100
            self.confidence_var.set(confidence)
            self.confidence_label.config(text=f"{confidence:.1f}%")
            
            # Update status
            status = self.current_invoice_data['validation']['status']
            self.status_var.set(f"Processing complete. Status: {status}")
            
        except Exception as e:
            self.status_var.set(f"Error processing invoice: {str(e)}")
    
    def save_invoice(self):
        """Save the processed invoice data to the database"""
        if not self.current_invoice_data:
            self.status_var.set("No invoice data to save. Please process an invoice first.")
            return
        
        if save_to_database(self.current_invoice_data, self.current_pdf_path):
            self.status_var.set("Invoice saved to database successfully.")
            
            # Refresh the database display
            self.load_database()
        else:
            self.status_var.set("Error saving invoice to database.")
    
    def export_data(self):
        """Export the processed invoice data to a file"""
        if not self.current_invoice_data:
            self.status_var.set("No invoice data to export. Please process an invoice first.")
            return
        
        # Ask for export format
        export_format = tk.StringVar(value="csv")
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Options")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select export format:").pack(pady=10)
        
        ttk.Radiobutton(dialog, text="CSV", variable=export_format, value="csv").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(dialog, text="JSON", variable=export_format, value="json").pack(anchor=tk.W, padx=20)
        
        def do_export():
            format_val = export_format.get()
            filename = export_to_accounting_system(self.current_invoice_data, format_val)
            if filename:
                self.status_var.set(f"Invoice data exported to {filename}")
            else:
                self.status_var.set("Error exporting invoice data")
            dialog.destroy()
        
        ttk.Button(dialog, text="Export", command=do_export).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)
    
    def load_database(self):
        """Load invoice data from the database and display in the table"""
        try:
            # Clear existing data
            for item in self.invoice_table.get_children():
                self.invoice_table.delete(item)
            
            # Load database
            if os.path.exists(DATABASE_PATH):
                df = pd.read_csv(DATABASE_PATH)
                
                # Add data to table
                for _, row in df.iterrows():
                    self.invoice_table.insert('', tk.END, values=(
                        row['invoice_id'],
                        row['vendor'],
                        row['date'],
                        f"${row['amount']:.2f}",
                        row['status'],
                        f"{row['confidence_score']*100:.1f}%"
                    ))
            
        except Exception as e:
            self.status_var.set(f"Error loading database: {str(e)}")
    
    def view_invoice(self):
        """View details of the selected invoice from the database"""
        selected_item = self.invoice_table.selection()
        if not selected_item:
            self.status_var.set("No invoice selected. Please select an invoice from the table.")
            return
        
        # Get the invoice_id of the selected item
        invoice_id = self.invoice_table.item(selected_item[0], 'values')[0]
        
        try:
            # Load database
            df = pd.read_csv(DATABASE_PATH)
            
            # Find the selected invoice
            invoice_row = df[df['invoice_id'] == invoice_id]
            if not invoice_row.empty:
                # Get the JSON data
                json_data = invoice_row.iloc[0]['json_data']
                invoice_data = json.loads(json_data)
                
                # Create a new window to display details
                details_window = tk.Toplevel(self.root)
                details_window.title(f"Invoice Details: {invoice_id}")
                details_window.geometry("600x500")
                
                # Create a text widget to display the JSON data
                details_text = tk.Text(details_window, wrap=tk.WORD)
                scrollbar = ttk.Scrollbar(details_window, command=details_text.yview)
                details_text.configure(yscrollcommand=scrollbar.set)
                
                details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Insert the formatted JSON data
                details_text.insert(tk.END, json.dumps(invoice_data, indent=2))
        
        except Exception as e:
            self.status_var.set(f"Error viewing invoice details: {str(e)}")
    
    def generate_analytics(self):
        """Generate analytics visualizations"""
        try:
            if not os.path.exists(DATABASE_PATH):
                self.status_var.set("No database found. Process some invoices first.")
                return
            
            df = pd.read_csv(DATABASE_PATH)
            if df.empty:
                self.status_var.set("No invoice data available for analytics.")
                return
            
            # Generate vendor analysis chart
            self.generate_vendor_chart(df)
            
            # Generate time analysis chart
            self.generate_time_chart(df)
            
            # Generate performance metrics
            self.generate_performance_metrics(df)
            
            self.status_var.set("Analytics generated successfully.")
            
        except Exception as e:
            self.status_var.set(f"Error generating analytics: {str(e)}")
    
    def generate_vendor_chart(self, df):
        """Generate vendor analysis chart"""
        # Clear previous chart
        self.vendor_canvas.delete("all")
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        # Group by vendor and count invoices
        vendor_counts = df['vendor'].value_counts()
        
        # Create bar chart
        vendor_counts.plot(kind='bar', ax=ax)
        ax.set_title('Invoice Count by Vendor')
        ax.set_xlabel('Vendor')
        ax.set_ylabel('Number of Invoices')
        
        # Embed in canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        chart = FigureCanvasTkAgg(fig, self.vendor_canvas)
        chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def generate_time_chart(self, df):
        """Generate time analysis chart"""
        # Clear previous chart
        self.time_canvas.delete("all")
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        # Convert date to datetime and sort
        try:
            df['processed_date'] = pd.to_datetime(df['processed_date'])
            df = df.sort_values('processed_date')
            
            # Group by day and count
            df['date'] = df['processed_date'].dt.date
            daily_counts = df.groupby('date').size()
            
            # Plot time series
            daily_counts.plot(ax=ax)
            ax.set_title('Invoices Processed Over Time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Invoices')
            
            # Embed in canvas
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            chart = FigureCanvasTkAgg(fig, self.time_canvas)
            chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            print(f"Error generating time chart: {str(e)}")
    
    def generate_performance_metrics(self, df):
        """Generate performance metrics"""
        # Clear previous content
        self.performance_canvas.delete("all")
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        # Calculate metrics
        total_invoices = len(df)
        auto_approved = len(df[df['status'] == 'Auto-Approved'])
        needs_review = len(df[df['status'] == 'Needs Review'])
        manual_processing = len(df[df['status'] == 'Manual Processing Required'])
        
        # Create pie chart
        labels = ['Auto-Approved', 'Needs Review', 'Manual Processing']
        sizes = [auto_approved, needs_review, manual_processing]
        colors = ['#4CAF50', '#FFC107', '#F44336']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        ax.set_title('Invoice Processing Performance')
        
        # Embed in canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        chart = FigureCanvasTkAgg(fig, self.performance_canvas)
        chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Main entry point for demonstration
def main():
    # Initialize and train model if needed
    # Create sample invoice database if it doesn't exist
    initialize_database()
    
    # Start the GUI
    root = tk.Tk()
    app = InvoiceProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()