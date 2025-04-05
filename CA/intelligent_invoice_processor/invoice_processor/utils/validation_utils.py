"""
Validation utilities for invoice processing.

This module provides helper functions for data validation.
"""

import re
import datetime
from fuzzywuzzy import process

from invoice_processor.logger import app_logger

def validate_invoice_number(invoice_number, vendor=None):
    """
    Validate invoice number format
    
    Args:
        invoice_number (str): Invoice number to validate
        vendor (str, optional): Vendor name for vendor-specific validation
        
    Returns:
        tuple: (is_valid, confidence, message)
    """
    app_logger.debug(f"Validating invoice number: {invoice_number}")
    
    if not invoice_number:
        return False, 0.0, "Invoice number is missing"
    
    # Check for minimum length
    if len(invoice_number) < 3:
        return False, 0.3, "Invoice number too short"
    
    # Check for common formats based on vendor if specified
    if vendor:
        from invoice_processor.data.vendor_database import get_vendor_details
        vendor_info = get_vendor_details(vendor)
        
        if vendor_info:
            # Here you could add vendor-specific validation rules
            pass
    
    # General format validation (alphanumeric with some punctuation)
    if re.match(r'^[A-Za-z0-9\-\.\/]+$', invoice_number):
        return True, 1.0, "Invoice number format is valid"
    else:
        return False, 0.5, "Invoice number contains invalid characters"

def validate_date(date_str):
    """
    Validate date format and reasonableness
    
    Args:
        date_str (str): Date string to validate
        
    Returns:
        tuple: (is_valid, confidence, message, parsed_date)
    """
    app_logger.debug(f"Validating date: {date_str}")
    
    if not date_str:
        return False, 0.0, "Date is missing", None
    
    # Try multiple date formats
    date_formats = ["%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d", 
                   "%m.%d.%Y", "%d.%m.%Y", "%B %d, %Y", "%d %B %Y"]
    
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
        
        if parsed_date > today:
            # Future date
            days_in_future = (parsed_date - today).days
            if days_in_future > 30:
                return False, 0.2, f"Date is {days_in_future} days in the future", parsed_date
            else:
                # Small future date might be valid (e.g., invoice date is a few days ahead)
                return True, 0.8, "Date is slightly in the future", parsed_date
        
        if parsed_date < today - datetime.timedelta(days=365*2):
            # More than 2 years old
            years_old = (today - parsed_date).days / 365
            return False, 0.3, f"Date is over {years_old:.1f} years old", parsed_date
        
        # Valid date
        return True, 1.0, "Date is valid", parsed_date
    else:
        return False, 0.0, f"Couldn't parse date format: {date_str}", None

def validate_amount(amount_str):
    """
    Validate amount format and reasonableness
    
    Args:
        amount_str (str): Amount string to validate
        
    Returns:
        tuple: (is_valid, confidence, message, parsed_amount)
    """
    app_logger.debug(f"Validating amount: {amount_str}")
    
    if not amount_str:
        return False, 0.0, "Amount is missing", None
    
    # Clean the string
    amount_str = amount_str.strip()
    
    # Remove currency symbols
    amount_str = re.sub(r'[$€£¥]', '', amount_str)
    
    # Remove commas
    amount_str = amount_str.replace(',', '')
    
    # Try to convert to float
    try:
        amount = float(amount_str)
        
        # Check reasonableness
        if amount < 0:
            return False, 0.1, "Amount is negative", amount
        
        if amount == 0:
            return False, 0.3, "Amount is zero", amount
        
        if amount > 1000000:
            # Very large amount
            return True, 0.5, "Amount is very large (over $1M)", amount
        
        # Valid amount
        return True, 1.0, "Amount is valid", amount
        
    except ValueError:
        return False, 0.0, f"Couldn't parse amount: {amount_str}", None

def validate_vendor(vendor_name):
    """
    Validate vendor against known vendors
    
    Args:
        vendor_name (str): Vendor name to validate
        
    Returns:
        tuple: (is_valid, confidence, message, matched_vendor)
    """
    app_logger.debug(f"Validating vendor: {vendor_name}")
    
    if not vendor_name:
        return False, 0.0, "Vendor name is missing", None
    
    from invoice_processor.data.vendor_database import get_all_vendors
    known_vendors = get_all_vendors()
    
    if not known_vendors:
        return True, 0.5, "No known vendors to match against", vendor_name
    
    # Try to match against known vendors using fuzzy matching
    match, score = process.extractOne(vendor_name, known_vendors)
    confidence = score / 100.0  # Convert to 0-1 scale
    
    if confidence >= 0.9:
        return True, confidence, f"Vendor matched to {match}", match
    elif confidence >= 0.7:
        return True, confidence, f"Vendor possibly matched to {match}", match
    else:
        return False, confidence, "Vendor not recognized", vendor_name

def validate_line_items(items, total_amount):
    """
    Validate line items against total amount
    
    Args:
        items (list): List of line item dictionaries
        total_amount (float): Total amount from invoice
        
    Returns:
        tuple: (is_valid, confidence, message)
    """
    app_logger.debug(f"Validating {len(items)} line items against total {total_amount}")
    
    if not items:
        return True, 0.5, "No line items to validate"
    
    if total_amount is None:
        return True, 0.5, "No total amount to validate against"
    
    # Calculate sum of line items
    try:
        items_total = sum(item.get('total', 0) for item in items)
        
        # Check if totals match (allowing for small rounding differences)
        if abs(items_total - total_amount) <= 0.02:
            return True, 1.0, "Line items total matches invoice total"
        
        # Check if it might be a subtotal (before tax, shipping, etc.)
        if items_total < total_amount:
            difference = total_amount - items_total
            percentage = (difference / total_amount) * 100
            
            if 5 <= percentage <= 25:
                # Might be tax or other charges
                return True, 0.8, f"Line items total ({items_total:.2f}) might be subtotal before tax/shipping"
                
        # Totals don't match
        return False, 0.3, f"Line items total ({items_total:.2f}) doesn't match invoice total ({total_amount:.2f})"
        
    except Exception as e:
        app_logger.error(f"Error validating line items: {str(e)}")
        return False, 0.0, f"Error validating line items: {str(e)}"