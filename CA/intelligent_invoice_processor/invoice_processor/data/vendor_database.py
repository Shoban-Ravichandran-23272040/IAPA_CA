"""
Vendor database module.

This module contains predefined vendor information 
for matching and validation.
"""

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
    },
    "Anthropic, PBC": {
        "address": "548 Market Street",
        "tax_id": "PMB 90375",
        "payment_terms": "2/10 Net 30",
        "typical_items": ["software license"]
    }
}

def get_vendor_details(vendor_name):
    """
    Get detailed information for a specific vendor
    
    Args:
        vendor_name (str): Name of the vendor
        
    Returns:
        dict: Vendor details or None if not found
    """
    return VENDOR_DATABASE.get(vendor_name)

def get_all_vendors():
    """
    Get a list of all vendor names
    
    Returns:
        list: List of all vendor names
    """
    return list(VENDOR_DATABASE.keys())

def add_vendor(name, address, tax_id, payment_terms, typical_items):
    """
    Add a new vendor to the database
    
    Args:
        name (str): Vendor name
        address (str): Vendor address
        tax_id (str): Vendor tax ID
        payment_terms (str): Vendor payment terms
        typical_items (list): List of typical items sold by vendor
        
    Returns:
        bool: True if successful, False if vendor already exists
    """
    if name in VENDOR_DATABASE:
        return False
    
    VENDOR_DATABASE[name] = {
        "address": address,
        "tax_id": tax_id,
        "payment_terms": payment_terms,
        "typical_items": typical_items
    }
    
    return True

def update_vendor(name, **kwargs):
    """
    Update an existing vendor
    
    Args:
        name (str): Vendor name
        **kwargs: Fields to update (address, tax_id, payment_terms, typical_items)
        
    Returns:
        bool: True if successful, False if vendor not found
    """
    if name not in VENDOR_DATABASE:
        return False
    
    for key, value in kwargs.items():
        if key in ["address", "tax_id", "payment_terms", "typical_items"]:
            VENDOR_DATABASE[name][key] = value
    
    return True