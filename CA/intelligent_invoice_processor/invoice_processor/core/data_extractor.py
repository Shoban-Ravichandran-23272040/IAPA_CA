"""
Data extraction module for invoice processing.

This module extracts structured data from invoice text,
validates the extracted data, and provides confidence scoring.
"""

import re
import datetime
from fuzzywuzzy import process

from invoice_processor.data.vendor_database import VENDOR_DATABASE
from invoice_processor.logger import app_logger
from invoice_processor.config import ML_CONFIDENCE_THRESHOLD

def extract_line_items(lines, start_line, end_line, app_logger):
    """
    Extract line items from invoice text with robust parsing
    
    Args:
        lines (list): Lines of text to parse
        start_line (int): Starting line number for item extraction
        end_line (int): Ending line number for item extraction
        app_logger (Logger): Logger for tracking extraction process
    
    Returns:
        list: Extracted line items
    """
    items = []
    
    # Comprehensive regex patterns for item extraction
    item_patterns = [
        # Most flexible pattern - handles multiple spacing, currency symbols, decimal formats
        r'^([A-Za-z0-9\s\-\(\)/&]+?)[\s\t]{1,}(\d+)[\s\t]{1,}[€$]?([\d.,]+)[\s\t]{1,}[€$]?([\d.,]+)$',
        
        # Pattern with stricter whitespace matching
        r'^([A-Za-z0-9\s\-\(\)/&]+)\s+(\d+)\s+[€$]?([\d.,]+)\s+[€$]?([\d.,]+)$',
        
        # Extra pattern for tighter matching
        r'^(.*?)\s{2,}(\d+)\s{2,}[€$]?([\d.,]+)\s{2,}[€$]?([\d.,]+)$'
    ]
    
    app_logger.debug(f"Extracting items from lines {start_line} to {end_line}")
    
    for i in range(start_line, end_line):
        line = lines[i].strip()
        if not line:
            continue
        
        matched = False
        for pattern in item_patterns:
            match = re.match(pattern, line, re.UNICODE)
            if match:
                try:
                    # Extract and clean the matched groups
                    item_description = match.group(1).strip()
                    
                    # Validate and parse quantity
                    try:
                        quantity = int(match.group(2).strip())
                    except ValueError:
                        app_logger.warning(f"Invalid quantity in line: {line}")
                        continue
                    
                    # Handle different decimal formats (. or ,)
                    def parse_decimal(value):
                        try:
                            # Remove currency symbols, spaces, and replace comma with dot
                            cleaned = value.replace('€', '').replace('$', '').replace(' ', '').replace(',', '.')
                            return float(cleaned)
                        except (ValueError, TypeError):
                            app_logger.warning(f"Could not parse decimal value: {value}")
                            return None
                    
                    unit_price = parse_decimal(match.group(3))
                    total_price = parse_decimal(match.group(4))
                    
                    # Skip if parsing fails
                    if unit_price is None or total_price is None:
                        continue
                    
                    # Validate total price calculation (with small tolerance)
                    calculated_total = round(quantity * unit_price, 2)
                    if abs(calculated_total - total_price) > 0.02:
                        app_logger.warning(f"Possible price calculation discrepancy: "
                                           f"Calculated {calculated_total}, Given {total_price}")
                    
                    new_item = {
                        "description": item_description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total": total_price
                    }
                    
                    items.append(new_item)
                    app_logger.debug(f"Extracted item: {new_item}")
                    matched = True
                    break
                
                except Exception as e:
                    app_logger.warning(f"Error processing line '{line}': {e}")
                    continue
        
        # If no pattern matched, log the line for debugging
        if not matched and line.strip():
            app_logger.warning(f"Could not extract item from line: '{line}'")
    
    app_logger.info(f"Extracted {len(items)} line items")
    return items

def parse_invoice_text(text, vendor_classifier=None):
    """
    Extract structured data from invoice text with validation and confidence scoring
    
    Args:
        text (str): OCR-extracted text from the invoice
        vendor_classifier (VendorClassifier, optional): Trained classifier for vendor identification
        
    Returns:
        dict: Structured invoice data with validation results
    """
    app_logger.info("Parsing invoice text and extracting data")
    
    # Use ML model if available, otherwise fall back to fuzzy matching
    if vendor_classifier:
        app_logger.debug("Using ML classifier for vendor identification")
        vendor, confidence = vendor_classifier.predict(text[:500])  # Use first 500 chars for classification
    else:
        app_logger.debug("Using fuzzy matching for vendor identification")
        # Fuzzy match vendor name from the first few lines
        first_lines = '\n'.join(text.split('\n')[:5])
        vendor_match = process.extractOne(first_lines, list(VENDOR_DATABASE.keys()))
        vendor = vendor_match[0]
        confidence = vendor_match[1] / 100.0  # Convert to 0-1 scale
    
    app_logger.debug(f"Identified vendor: {vendor} with confidence: {confidence:.2f}")
    
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
    # Add this debug section to see what's being extracted
    print("===== RAW EXTRACTED TEXT =====")
    print(text)
    print("=============================")
        
    # Add a safety check for empty or very short text
    if not text or len(text) < 50:
        result["validation"]["warnings"].append("Insufficient text extracted from invoice")
        result["validation"]["status"] = "Manual Processing Required"
        return result
    
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
    app_logger.debug("Extracting metadata fields")
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                app_logger.debug(f"Extracted {field}: {value}")
                
                if field == "total_amount":
                    value = value.replace(',', '')
                    try:
                        value = float(value)
                    except ValueError:
                        app_logger.warning(f"Could not convert total amount: {value}")
                        result["validation"]["warnings"].append(f"Could not convert total amount: {value}")
                        value = 0.0
                        
                result["metadata"][field] = value
                break
    
    # Log extraction results
    for field in patterns.keys():
        if field not in result["metadata"]:
            app_logger.debug(f"Failed to extract {field}")
    
    # Extract itemized section with improved pattern matching
    app_logger.debug("Extracting line items")
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
                    app_logger.debug(f"Found item table header at line {i}: {line}")
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
                    app_logger.debug(f"Found end of item table at line {i}: {lines[i]}")
                    break
            
            # If no end marker found, use a reasonable number of lines
            if end_line < 0:
                end_line = min(start_line + 15, len(lines))
                app_logger.debug(f"No explicit end of table found, using line {end_line}")
            
            # Extract items
            app_logger.debug(f"Extracting items from lines {start_line} to {end_line}")
            for i in range(start_line, end_line):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Try various item line formats with more flexible matching
                patterns = [
                    # Standard format with flexible whitespace and optional currency symbols
                    r'([A-Za-z0-9\s\-\(\)]+)[\s\t]+(\d+)[\s\t]+[€$]?([\d.,]+)[\s\t]+[€$]?([\d.,]+)',
                    # Format specifically for Euro currency with flexible whitespace
                    r'([A-Za-z0-9\s\-\(\)]+)[\s\t]+(\d+)[\s\t]+€([\d.,]+)[\s\t]+€([\d.,]+)',
                    # Extra flexible pattern to catch more variations
                    r'([A-Za-z0-9\s\-\(\)]+?)[\s\t]{2,}(\d+)[\s\t]{2,}[€$]?([\d.,]+)[\s\t]{2,}[€$]?([\d.,]+)',
                    # Most flexible pattern - handles multiple spacing, currency symbols, decimal formats
                    r'^([A-Za-z0-9\s\-\(\)/&]+?)[\s\t]{1,}(\d+)[\s\t]{1,}[€$]?([\d.,]+)[\s\t]{1,}[€$]?([\d.,]+)$',
                    # Pattern with stricter whitespace matching
                    r'^([A-Za-z0-9\s\-\(\)/&]+)\s+(\d+)\s+[€$]?([\d.,]+)\s+[€$]?([\d.,]+)$',
                    # Extra pattern for tighter matching
                    r'^(.*?)\s{2,}(\d+)\s{2,}[€$]?([\d.,]+)\s{2,}[€$]?([\d.,]+)$'
                ]
                
                matched = False
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        item, qty, price, total = match.groups()
                        new_item = {
                            "description": item.strip(),
                            "quantity": int(qty),
                            "unit_price": float(price.replace(',', '.')),  # Handle European decimal format
                            "total": float(total.replace(',', '.'))  # Handle European decimal format
                        }
                        result["items"].append(new_item)
                        app_logger.debug(f"Extracted item: {new_item['description']}, quantity: {new_item['quantity']}, price: {new_item['unit_price']}, total: {new_item['total']}")
                        matched = True
                        break
                
                # If no pattern matched, log the line for debugging
                if not matched and line.strip():
                    app_logger.warning(f"Could not extract item from line: '{line}'")

            app_logger.info(f"Extracted {len(result['items'])} line items")
        else:
            app_logger.debug("No item table header found")
        
        # Extract total section information
        app_logger.debug("Extracting totals section")
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
                    app_logger.debug(f"Extracted {field}: {value}")
                except ValueError:
                    app_logger.warning(f"Could not convert {field}: {match.group(1)}")
                    result["validation"]["warnings"].append(f"Could not convert {field}: {match.group(1)}")
    
    except Exception as e:
        app_logger.error(f"Error extracting items: {str(e)}")
        result["validation"]["warnings"].append(f"Error extracting items: {str(e)}")
    
    # Validation steps
    app_logger.debug("Performing validation checks")
    validation_score = 0
    
    # 1. Check if we have the essential fields
    essential_fields = ["invoice_no", "date", "total_amount"]
    for field in essential_fields:
        if field in result["metadata"]:
            validation_score += 1
            app_logger.debug(f"Validation: {field} is present")
        else:
            app_logger.debug(f"Validation: {field} is missing")
    
    # 2. Verify items total matches the invoice total if both are available
    if result["items"] and "total" in result["totals"]:
        items_total = sum(item["total"] for item in result["items"])
        invoice_total = result["totals"]["total"]
        
        # Allow for small rounding differences
        if abs(items_total - invoice_total) <= 0.02:
            validation_score += 1
            app_logger.debug(f"Validation: Items total ({items_total}) matches invoice total ({invoice_total})")
        else:
            app_logger.warning(f"Validation: Items total ({items_total}) doesn't match invoice total ({invoice_total})")
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
                    app_logger.debug(f"Validation: Date {date_str} is valid")
                else:
                    app_logger.warning(f"Validation: Date {date_str} seems unusual")
                    result["validation"]["warnings"].append(f"Invoice date {date_str} seems unusual")
            else:
                app_logger.warning(f"Validation: Couldn't parse date {date_str}")
                result["validation"]["warnings"].append(f"Couldn't parse date: {date_str}")
        except Exception as e:
            app_logger.error(f"Date validation error: {str(e)}")
            result["validation"]["warnings"].append(f"Date validation error: {str(e)}")
    
    # Calculate overall confidence score
    max_score = 3 + (1 if result["items"] else 0)  # Maximum possible validation score
    if max_score > 0:
        overall_confidence = (validation_score / max_score) * confidence
    else:
        overall_confidence = confidence * 0.5
    
    result["validation"]["overall_confidence"] = overall_confidence
    app_logger.info(f"Overall confidence score: {overall_confidence:.2f}")
    
    # Set status based on confidence and warnings
    if overall_confidence >= ML_CONFIDENCE_THRESHOLD and not result["validation"]["warnings"]:
        result["validation"]["status"] = "Auto-Approved"
        app_logger.info("Invoice status: Auto-Approved")
    elif overall_confidence >= 0.6:
        result["validation"]["status"] = "Needs Review"
        app_logger.info("Invoice status: Needs Review")
    else:
        result["validation"]["status"] = "Manual Processing Required"
        app_logger.info("Invoice status: Manual Processing Required")
    
    return result