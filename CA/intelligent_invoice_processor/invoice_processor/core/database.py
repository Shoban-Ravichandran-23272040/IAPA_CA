"""
Database operations module for invoice processing.

This module handles saving processed invoices to the database
and exporting data to external formats.
"""

import os
import json
import datetime
import pandas as pd

from invoice_processor.config import DATABASE_PATH
from invoice_processor.logger import app_logger

def initialize_database():
    """
    Create or verify database file exists
    
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        if not os.path.exists(DATABASE_PATH):
            app_logger.info(f"Creating new database at {DATABASE_PATH}")
            # Create empty dataframe with necessary columns
            columns = ['invoice_id', 'vendor', 'date', 'amount', 'status', 
                       'processed_date', 'json_data', 'confidence_score']
            df = pd.DataFrame(columns=columns)
            df.to_csv(DATABASE_PATH, index=False)
            app_logger.debug("Database created successfully")
            return True
        else:
            app_logger.debug(f"Using existing database at {DATABASE_PATH}")
            return True
    except Exception as e:
        app_logger.error(f"Error initializing database: {str(e)}")
        return False

def save_to_database(invoice_data, pdf_path):
    """
    Save processed invoice to database
    
    Args:
        invoice_data (dict): Processed invoice data
        pdf_path (str): Path to the original PDF file
        
    Returns:
        bool: True if successful, False if error occurred
    """
    app_logger.info("Saving invoice to database")
    try:
        # Ensure database exists
        if not os.path.exists(DATABASE_PATH):
            app_logger.debug("Database doesn't exist, initializing")
            initialize_database()
        
        # Read existing database
        df = pd.read_csv(DATABASE_PATH)
        app_logger.debug(f"Loaded database with {len(df)} existing records")
        
        # Extract invoice ID for checking duplicates
        invoice_id = invoice_data['metadata'].get('invoice_no', 'Unknown')
        
        # Check if this invoice already exists
        if 'invoice_id' in df.columns and invoice_id in df['invoice_id'].values:
            app_logger.warning(f"Invoice {invoice_id} already exists in database")
            # Update existing record
            idx = df.index[df['invoice_id'] == invoice_id].tolist()[0]
            
            df.at[idx, 'vendor'] = invoice_data['vendor']['name']
            df.at[idx, 'date'] = invoice_data['metadata'].get('date', 'Unknown')
            df.at[idx, 'amount'] = invoice_data['metadata'].get('total_amount', 
                                invoice_data['totals'].get('total', 0))
            df.at[idx, 'status'] = invoice_data['validation']['status']
            df.at[idx, 'processed_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            df.at[idx, 'json_data'] = json.dumps(invoice_data)
            df.at[idx, 'confidence_score'] = invoice_data['validation']['overall_confidence']
            
            app_logger.info(f"Updated existing invoice record: {invoice_id}")
        else:
            # Create new record
            new_record = {
                'invoice_id': invoice_id,
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
            df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            app_logger.info(f"Added new invoice record: {invoice_id}")
        
        # Save back to CSV
        df.to_csv(DATABASE_PATH, index=False)
        app_logger.debug(f"Database saved with {len(df)} total records")
        return True
    except Exception as e:
        app_logger.error(f"Error saving to database: {str(e)}")
        return False

def get_all_invoices():
    """
    Retrieve all invoices from the database
    
    Returns:
        pandas.DataFrame: DataFrame containing all invoices, or empty DataFrame if error
    """
    try:
        if not os.path.exists(DATABASE_PATH):
            app_logger.warning("Database file does not exist")
            return pd.DataFrame()
        
        df = pd.read_csv(DATABASE_PATH)
        app_logger.debug(f"Retrieved {len(df)} invoices from database")
        return df
    except Exception as e:
        app_logger.error(f"Error retrieving invoices: {str(e)}")
        return pd.DataFrame()

def get_invoice_by_id(invoice_id):
    """
    Retrieve a specific invoice by ID
    
    Args:
        invoice_id (str): Invoice ID to retrieve
        
    Returns:
        dict: Invoice data or None if not found
    """
    try:
        if not os.path.exists(DATABASE_PATH):
            app_logger.warning("Database file does not exist")
            return None
        
        df = pd.read_csv(DATABASE_PATH)
        
        # Find the invoice
        invoice_row = df[df['invoice_id'] == invoice_id]
        if invoice_row.empty:
            app_logger.warning(f"Invoice {invoice_id} not found in database")
            return None
        
        # Get the JSON data
        json_data = invoice_row.iloc[0]['json_data']
        invoice_data = json.loads(json_data)
        
        app_logger.debug(f"Retrieved invoice {invoice_id} from database")
        return invoice_data
    except Exception as e:
        app_logger.error(f"Error retrieving invoice {invoice_id}: {str(e)}")
        return None

def export_to_accounting_system(invoice_data, output_format="csv"):
    """
    Export invoice data to a file format suitable for accounting systems
    
    Args:
        invoice_data (dict): Processed invoice data
        output_format (str): Format to export (csv or json)
        
    Returns:
        str: Path to exported file or None if error
    """
    app_logger.info(f"Exporting invoice data to {output_format} format")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        invoice_id = invoice_data['metadata'].get('invoice_no', 'unknown')
        
        # Create exports directory if it doesn't exist
        export_dir = os.path.join(os.path.dirname(DATABASE_PATH), "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        if output_format.lower() == "csv":
            filename = os.path.join(export_dir, f"export_{invoice_id}_{timestamp}.csv")
            
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
                items_filename = os.path.join(export_dir, f"export_{invoice_id}_items_{timestamp}.csv")
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
                app_logger.debug(f"Item data exported to {items_filename}")
            
            # Save main invoice data
            pd.DataFrame(export_data).to_csv(filename, index=False)
            app_logger.info(f"Invoice data exported to {filename}")
            
            return filename
        
        elif output_format.lower() == "json":
            filename = os.path.join(export_dir, f"export_{invoice_id}_{timestamp}.json")
            with open(filename, 'w') as f:
                json.dump(invoice_data, f, indent=2)
            app_logger.info(f"Invoice data exported to {filename}")
            return filename
        
        else:
            app_logger.warning(f"Unsupported output format: {output_format}")
            return None
            
    except Exception as e:
        app_logger.error(f"Error exporting data: {str(e)}")
        return None