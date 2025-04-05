"""
Export utilities for invoice processing.

This module provides helper functions for exporting invoice data.
"""

import os
import json
import datetime
import pandas as pd
import csv

from invoice_processor.logger import app_logger
from invoice_processor.config import DATA_DIR

def export_to_csv(invoice_data, output_path=None):
    """
    Export invoice data to CSV format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str, optional): Path to save the CSV file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Exporting invoice data to CSV")
    
    try:
        # Generate filename if not provided
        if not output_path:
            # Create exports directory if it doesn't exist
            export_dir = os.path.join(DATA_DIR, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
            output_path = os.path.join(export_dir, f"invoice_{invoice_id}_{timestamp}.csv")
        
        # Create header data
        header_data = {
            'Invoice Number': invoice_data['metadata'].get('invoice_no', ''),
            'Vendor': invoice_data['vendor']['name'],
            'Date': invoice_data['metadata'].get('date', ''),
            'Due Date': invoice_data['metadata'].get('due_date', ''),
            'PO Number': invoice_data['metadata'].get('po_number', ''),
            'Total Amount': invoice_data['metadata'].get('total_amount', 
                           invoice_data['totals'].get('total', 0)),
            'Status': invoice_data['validation']['status'],
            'Confidence': invoice_data['validation']['overall_confidence']
        }
        
        # Write to CSV
        df = pd.DataFrame([header_data])
        df.to_csv(output_path, index=False)
        
        # If there are line items, write them to a separate file
        if invoice_data['items']:
            items_path = os.path.splitext(output_path)[0] + "_items.csv"
            
            items_data = []
            for item in invoice_data['items']:
                items_data.append({
                    'Invoice Number': invoice_data['metadata'].get('invoice_no', ''),
                    'Description': item['description'],
                    'Quantity': item['quantity'],
                    'Unit Price': item['unit_price'],
                    'Total Price': item['total']
                })
            
            items_df = pd.DataFrame(items_data)
            items_df.to_csv(items_path, index=False)
            
            app_logger.debug(f"Exported {len(items_data)} line items to {items_path}")
        
        app_logger.info(f"Invoice data exported to {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error exporting to CSV: {str(e)}")
        return None

def export_to_json(invoice_data, output_path=None):
    """
    Export invoice data to JSON format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str, optional): Path to save the JSON file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Exporting invoice data to JSON")
    
    try:
        # Generate filename if not provided
        if not output_path:
            # Create exports directory if it doesn't exist
            export_dir = os.path.join(DATA_DIR, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
            output_path = os.path.join(export_dir, f"invoice_{invoice_id}_{timestamp}.json")
        
        # Write to JSON file
        with open(output_path, 'w') as f:
            json.dump(invoice_data, f, indent=2)
        
        app_logger.info(f"Invoice data exported to {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error exporting to JSON: {str(e)}")
        return None

def export_to_accounting_format(invoice_data, accounting_system="generic", output_path=None):
    """
    Export invoice data in a format suitable for accounting systems
    
    Args:
        invoice_data (dict): Processed invoice data
        accounting_system (str): Target accounting system (generic, quickbooks, xero, sage)
        output_path (str, optional): Path to save the exported file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug(f"Exporting invoice data for {accounting_system}")
    
    try:
        # Generate filename if not provided
        if not output_path:
            # Create exports directory if it doesn't exist
            export_dir = os.path.join(DATA_DIR, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
            
            if accounting_system.lower() == "quickbooks":
                output_path = os.path.join(export_dir, f"qb_invoice_{invoice_id}_{timestamp}.iif")
            elif accounting_system.lower() == "xero":
                output_path = os.path.join(export_dir, f"xero_invoice_{invoice_id}_{timestamp}.csv")
            elif accounting_system.lower() == "sage":
                output_path = os.path.join(export_dir, f"sage_invoice_{invoice_id}_{timestamp}.csv")
            else:
                output_path = os.path.join(export_dir, f"invoice_{invoice_id}_{timestamp}.csv")
        
        # Format data according to accounting system
        if accounting_system.lower() == "quickbooks":
            result = _format_for_quickbooks(invoice_data, output_path)
        elif accounting_system.lower() == "xero":
            result = _format_for_xero(invoice_data, output_path)
        elif accounting_system.lower() == "sage":
            result = _format_for_sage(invoice_data, output_path)
        else:
            # Use generic CSV format
            result = export_to_csv(invoice_data, output_path)
        
        return result
    
    except Exception as e:
        app_logger.error(f"Error exporting to accounting format: {str(e)}")
        return None

def _format_for_quickbooks(invoice_data, output_path):
    """
    Format invoice data for QuickBooks IIF format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str): Path to save the IIF file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Formatting for QuickBooks IIF")
    
    try:
        invoice_no = invoice_data['metadata'].get('invoice_no', '')
        vendor = invoice_data['vendor']['name']
        date = invoice_data['metadata'].get('date', '')
        
        # Convert date to MM/DD/YYYY if needed
        try:
            parsed_date = datetime.datetime.strptime(date, "%m/%d/%Y")
            date = parsed_date.strftime("%m/%d/%Y")
        except ValueError:
            # If we can't parse the date, use it as is
            pass
        
        total = invoice_data['metadata'].get('total_amount', 
                invoice_data['totals'].get('total', 0))
        
        # Create IIF file content
        with open(output_path, 'w', newline='') as f:
            # Write header
            f.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n")
            f.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n")
            f.write("!ENDTRNS\n")
            
            # Write transaction
            f.write(f"TRNS\tBILL\t{date}\tAccounts Payable\t{vendor}\t{total}\t{invoice_no}\tInvoice {invoice_no}\n")
            
            # Write split lines for each item
            for item in invoice_data['items']:
                description = item['description']
                amount = item['total']
                f.write(f"SPL\tBILL\t{date}\tExpense\t{vendor}\t{amount}\t{invoice_no}\t{description}\n")
            
            # End transaction
            f.write("ENDTRNS\n")
        
        app_logger.info(f"Invoice data exported to QuickBooks format at {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error formatting for QuickBooks: {str(e)}")
        return None

def _format_for_xero(invoice_data, output_path):
    """
    Format invoice data for Xero CSV format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str): Path to save the CSV file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Formatting for Xero CSV")
    
    try:
        # Xero requires specific column headers
        headers = [
            '*ContactName', '*InvoiceNumber', '*InvoiceDate', 'DueDate', 
            '*LineAmount', 'Description', 'Quantity', 'UnitAmount', 
            '*AccountCode', 'TaxType', 'TaxAmount', 'Currency', 'PONumber'
        ]
        
        # Extract data
        vendor = invoice_data['vendor']['name']
        invoice_no = invoice_data['metadata'].get('invoice_no', '')
        date = invoice_data['metadata'].get('date', '')
        due_date = invoice_data['metadata'].get('due_date', '')
        po_number = invoice_data['metadata'].get('po_number', '')
        
        # Convert dates to YYYY-MM-DD if needed
        try:
            parsed_date = datetime.datetime.strptime(date, "%m/%d/%Y")
            date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            # If we can't parse the date, use it as is
            pass
        
        try:
            if due_date:
                parsed_due_date = datetime.datetime.strptime(due_date, "%m/%d/%Y")
                due_date = parsed_due_date.strftime("%Y-%m-%d")
        except ValueError:
            # If we can't parse the date, use it as is
            pass
        
        # Set default tax rate if not present
        tax_rate = 0.0
        if 'tax' in invoice_data['totals'] and 'subtotal' in invoice_data['totals']:
            tax_amount = invoice_data['totals']['tax']
            subtotal = invoice_data['totals']['subtotal']
            if subtotal > 0:
                tax_rate = tax_amount / subtotal
        
        # Create CSV file
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Write rows for each line item
            for item in invoice_data['items']:
                description = item['description']
                quantity = item['quantity']
                unit_price = item['unit_price']
                line_amount = item['total']
                tax_amount = line_amount * tax_rate
                
                writer.writerow([
                    vendor,                   # *ContactName
                    invoice_no,               # *InvoiceNumber
                    date,                     # *InvoiceDate
                    due_date,                 # DueDate
                    line_amount,              # *LineAmount
                    description,              # Description
                    quantity,                 # Quantity
                    unit_price,               # UnitAmount
                    '6000',                   # *AccountCode (default expense account)
                    'Tax Exclusive',          # TaxType
                    tax_amount,               # TaxAmount
                    'USD',                    # Currency
                    po_number                 # PONumber
                ])
        
        app_logger.info(f"Invoice data exported to Xero format at {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error formatting for Xero: {str(e)}")
        return None

def _format_for_sage(invoice_data, output_path):
    """
    Format invoice data for Sage CSV format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str): Path to save the CSV file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Formatting for Sage CSV")
    
    try:
        # Sage headers
        headers = [
            'A/C Reference', 'Name', 'Invoice Number', 'Date', 'Nominal Code',
            'Description', 'Net Amount', 'Tax Code', 'Tax Amount', 'Gross Amount'
        ]
        
        # Extract data
        vendor = invoice_data['vendor']['name']
        invoice_no = invoice_data['metadata'].get('invoice_no', '')
        date = invoice_data['metadata'].get('date', '')
        
        # Get vendor reference (first 8 chars of vendor name)
        vendor_ref = vendor[:8].upper().replace(' ', '')
        
        # Get totals
        net_amount = invoice_data['totals'].get('subtotal', 0)
        tax_amount = invoice_data['totals'].get('tax', 0)
        gross_amount = invoice_data['totals'].get('total', 0)
        
        # If we don't have subtotal but have items, calculate it
        if net_amount == 0 and invoice_data['items']:
            net_amount = sum(item['total'] for item in invoice_data['items'])
        
        # If we don't have tax amount but have total and subtotal, calculate it
        if tax_amount == 0 and net_amount > 0 and gross_amount > 0:
            tax_amount = gross_amount - net_amount
        
        # If we don't have gross amount but have subtotal and tax, calculate it
        if gross_amount == 0 and net_amount > 0:
            gross_amount = net_amount + tax_amount
        
        # Create CSV file
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Write header row for the invoice
            writer.writerow([
                vendor_ref,                  # A/C Reference
                vendor,                       # Name
                invoice_no,                   # Invoice Number
                date,                         # Date
                '5000',                       # Nominal Code (default expense account)
                f"Invoice {invoice_no}",      # Description
                net_amount,                   # Net Amount
                'T1',                         # Tax Code
                tax_amount,                   # Tax Amount
                gross_amount                  # Gross Amount
            ])
            
            # Optionally write detail rows for each line item
            for item in invoice_data['items']:
                description = item['description']
                amount = item['total']
                
                # Calculate item tax (proportional)
                item_tax = 0
                if net_amount > 0:
                    item_tax = (amount / net_amount) * tax_amount
                
                item_gross = amount + item_tax
                
                writer.writerow([
                    vendor_ref,                  # A/C Reference
                    vendor,                       # Name
                    invoice_no,                   # Invoice Number
                    date,                         # Date
                    '5000',                       # Nominal Code
                    description,                  # Description
                    amount,                       # Net Amount
                    'T1',                         # Tax Code
                    item_tax,                     # Tax Amount
                    item_gross                    # Gross Amount
                ])
        
        app_logger.info(f"Invoice data exported to Sage format at {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error formatting for Sage: {str(e)}")
        return None

def export_to_excel(invoice_data, output_path=None):
    """
    Export invoice data to Excel format
    
    Args:
        invoice_data (dict): Processed invoice data
        output_path (str, optional): Path to save the Excel file
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.debug("Exporting invoice data to Excel")
    
    try:
        # Generate filename if not provided
        if not output_path:
            # Create exports directory if it doesn't exist
            export_dir = os.path.join(DATA_DIR, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
            output_path = os.path.join(export_dir, f"invoice_{invoice_id}_{timestamp}.xlsx")
        
        # Create a Pandas Excel writer
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        
        # Create header data
        header_data = {
            'Invoice Number': [invoice_data['metadata'].get('invoice_no', '')],
            'Vendor': [invoice_data['vendor']['name']],
            'Date': [invoice_data['metadata'].get('date', '')],
            'Due Date': [invoice_data['metadata'].get('due_date', '')],
            'PO Number': [invoice_data['metadata'].get('po_number', '')],
            'Total Amount': [invoice_data['metadata'].get('total_amount', 
                            invoice_data['totals'].get('total', 0))],
            'Status': [invoice_data['validation']['status']],
            'Confidence': [invoice_data['validation']['overall_confidence']]
        }
        
        # Create the main sheet
        df_header = pd.DataFrame(header_data)
        df_header.to_excel(writer, sheet_name='Invoice', index=False)
        
        # Create items sheet if items are available
        if invoice_data['items']:
            items_data = []
            for item in invoice_data['items']:
                items_data.append({
                    'Description': item['description'],
                    'Quantity': item['quantity'],
                    'Unit Price': item['unit_price'],
                    'Total Price': item['total']
                })
            
            df_items = pd.DataFrame(items_data)
            df_items.to_excel(writer, sheet_name='Line Items', index=False)
        
        # Create validation sheet with warnings
        if invoice_data['validation']['warnings']:
            warnings_data = {
                'Warning': invoice_data['validation']['warnings']
            }
            df_warnings = pd.DataFrame(warnings_data)
            df_warnings.to_excel(writer, sheet_name='Validation', index=False)
        
        # Save the Excel file
        writer.close()
        
        app_logger.info(f"Invoice data exported to Excel at {output_path}")
        return output_path
    
    except Exception as e:
        app_logger.error(f"Error exporting to Excel: {str(e)}")
        return None