"""
Tests for the data extraction module.
"""

import unittest
import os
from pathlib import Path

from invoice_processor.core.data_extractor import parse_invoice_text

class TestDataExtractor(unittest.TestCase):
    """Test case for the data extraction module"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Load test data
        self.test_data_dir = Path(__file__).parent / 'test_data'
        
        # Sample invoice text
        self.sample_invoice_text = """
        XYZ Traders Inc.
        456 Trading Ave, Commerce City
        
        INVOICE
        
        Invoice No: INV123456
        Date: 03/29/2024
        Due Date: 04/28/2024
        
        Item Qty Price Total
        
        Mouse 2 25.00 50.00
        Keyboard 1 45.00 45.00
        Monitor 3 350.00 1050.00
        
        Subtotal: 1145.00
        Tax: 50.00
        Total Amount: 1195.00
        
        Payment Terms: Net 30
        """
    
    def test_vendor_extraction(self):
        """Test vendor extraction"""
        result = parse_invoice_text(self.sample_invoice_text)
        
        self.assertEqual(result['vendor']['name'], "XYZ Traders Inc.")
        self.assertGreater(result['vendor']['confidence'], 0.7)
    
    def test_metadata_extraction(self):
        """Test metadata extraction"""
        result = parse_invoice_text(self.sample_invoice_text)
        
        self.assertEqual(result['metadata']['invoice_no'], "INV123456")
        self.assertEqual(result['metadata']['date'], "03/29/2024")
        self.assertEqual(result['metadata']['due_date'], "04/28/2024")
    
    def test_items_extraction(self):
        """Test line items extraction"""
        result = parse_invoice_text(self.sample_invoice_text)
        
        self.assertEqual(len(result['items']), 3)
        
        # Check the first item
        self.assertEqual(result['items'][0]['description'], "Mouse")
        self.assertEqual(result['items'][0]['quantity'], 2)
        self.assertEqual(result['items'][0]['unit_price'], 25.0)
        self.assertEqual(result['items'][0]['total'], 50.0)
    
    def test_totals_extraction(self):
        """Test totals extraction"""
        result = parse_invoice_text(self.sample_invoice_text)
        
        self.assertEqual(result['totals']['subtotal'], 1145.0)
        self.assertEqual(result['totals']['tax'], 50.0)
        self.assertEqual(result['totals']['total'], 1145.0)
    
    def test_validation(self):
        """Test validation logic"""
        result = parse_invoice_text(self.sample_invoice_text)
        
        # Check validation results
        self.assertGreater(result['validation']['overall_confidence'], 0.6)
        self.assertIn(result['validation']['status'], 
                     ["Auto-Approved", "Needs Review", "Manual Processing Required"])
    
    def test_empty_text(self):
        """Test with empty text"""
        result = parse_invoice_text("")
        
        # Should have empty metadata but still have structure
        self.assertIn('metadata', result)
        self.assertIn('items', result)
        self.assertIn('validation', result)
        
        # Validation should indicate issues
        self.assertLess(result['validation']['overall_confidence'], 0.5)
        self.assertEqual(result['validation']['status'], "Manual Processing Required")

if __name__ == '__main__':
    unittest.main()