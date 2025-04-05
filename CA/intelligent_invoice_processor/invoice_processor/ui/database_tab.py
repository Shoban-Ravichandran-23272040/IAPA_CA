"""
Database tab for invoice management.

This module defines the UI components for the invoice database tab.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import pandas as pd

from invoice_processor.logger import app_logger
from invoice_processor.core.database import get_all_invoices, get_invoice_by_id, export_to_accounting_system

class DatabaseTab:
    """Database tab for invoice management"""
    
    def __init__(self, parent):
        """
        Initialize the database tab
        
        Args:
            parent (ttk.Frame): Parent frame
        """
        self.parent = parent
        self.process_tab = None  # Will be set later
        
        # Setup UI components
        self._setup_ui()
    
    def set_process_tab(self, process_tab):
        """
        Set reference to process tab for data sharing
        
        Args:
            process_tab (ProcessTab): Process tab instance
        """
        self.process_tab = process_tab
    
    def _setup_ui(self):
        """Set up UI components"""
        # Create a frame for the database controls
        self.control_frame = ttk.Frame(self.parent, padding=10)
        self.control_frame.pack(fill=tk.X)
        
        ttk.Label(self.control_frame, text="Invoice Database", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Refresh Data", command=self.load_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="View Selected Invoice", command=self.view_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Export Selected", command=self.export_selected).pack(side=tk.LEFT, padx=5)
        
        # Search frame
        self.search_frame = ttk.Frame(self.parent, padding=(10, 5))
        self.search_frame.pack(fill=tk.X)
        
        ttk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        self.search_in = tk.StringVar(value="All Fields")
        search_options = ttk.Combobox(self.search_frame, textvariable=self.search_in, values=["All Fields", "Invoice #", "Vendor", "Date", "Status"], state="readonly", width=15)
        search_options.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.search_frame, text="Search", command=self.search_invoices).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        # Status filter
        self.filter_frame = ttk.Frame(self.parent, padding=(10, 0, 10, 10))
        self.filter_frame.pack(fill=tk.X)
        
        ttk.Label(self.filter_frame, text="Filter by Status:").pack(side=tk.LEFT, padx=5)
        
        self.show_auto_approved = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.filter_frame, text="Auto-Approved", variable=self.show_auto_approved, command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        
        self.show_needs_review = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.filter_frame, text="Needs Review", variable=self.show_needs_review, command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        
        self.show_manual = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.filter_frame, text="Manual Processing", variable=self.show_manual, command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        
        # Create a frame for the database table
        self.table_frame = ttk.Frame(self.parent, padding=10)
        self.table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Database table
        columns = ('invoice_id', 'vendor', 'date', 'amount', 'status', 'confidence', 'processed_date')
        self.invoice_table = ttk.Treeview(self.table_frame, columns=columns, show='headings')
        
        # Define headings
        self.invoice_table.heading('invoice_id', text='Invoice #', command=lambda: self._sort_by_column('invoice_id'))
        self.invoice_table.heading('vendor', text='Vendor', command=lambda: self._sort_by_column('vendor'))
        self.invoice_table.heading('date', text='Date', command=lambda: self._sort_by_column('date'))
        self.invoice_table.heading('amount', text='Amount', command=lambda: self._sort_by_column('amount'))
        self.invoice_table.heading('status', text='Status', command=lambda: self._sort_by_column('status'))
        self.invoice_table.heading('confidence', text='Confidence', command=lambda: self._sort_by_column('confidence'))
        self.invoice_table.heading('processed_date', text='Processed On', command=lambda: self._sort_by_column('processed_date'))
        
        # Define columns
        self.invoice_table.column('invoice_id', width=100)
        self.invoice_table.column('vendor', width=150)
        self.invoice_table.column('date', width=100)
        self.invoice_table.column('amount', width=100)
        self.invoice_table.column('status', width=150)
        self.invoice_table.column('confidence', width=100)
        self.invoice_table.column('processed_date', width=150)
        
        # Add a scrollbar
        table_scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.invoice_table.yview)
        self.invoice_table.configure(yscrollcommand=table_scrollbar.set)
        
        # Add a horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.invoice_table.xview)
        self.invoice_table.configure(xscrollcommand=h_scrollbar.set)
        
        # Pack the table and scrollbars
        self.invoice_table.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("0 invoices loaded")
        status_bar = ttk.Label(self.parent, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # Double-click to view invoice
        self.invoice_table.bind("<Double-1>", lambda event: self.view_invoice())
        
        # Right-click menu
        self.context_menu = tk.Menu(self.invoice_table, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self.view_invoice)
        self.context_menu.add_command(label="Export", command=self.export_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_invoice)
        
        self.invoice_table.bind("<Button-3>", self._show_context_menu)
        
        # Store the full dataset and current filtered dataset
        self.full_dataset = pd.DataFrame()
        self.filtered_dataset = pd.DataFrame()
        
        # Sort direction
        self.sort_column = 'processed_date'  # Default sort column
        self.sort_reverse = True  # Default sort direction (newest first)
    
    def load_database(self):
        """Load invoice data from the database and display in the table"""
        app_logger.debug("Loading invoice database")
        try:
            # Get all invoices
            df = get_all_invoices()
            
            if df.empty:
                app_logger.debug("No invoices found in database")
                self.status_var.set("No invoices found in database")
                self.full_dataset = df
                self.filtered_dataset = df
                
                # Clear existing data
                for item in self.invoice_table.get_children():
                    self.invoice_table.delete(item)
                    
                return
            
            # Store the full dataset
            self.full_dataset = df
            
            # Apply filters
            self.apply_filters()
            
            app_logger.info(f"Loaded {len(df)} invoices from database")
            
        except Exception as e:
            app_logger.error(f"Error loading database: {str(e)}")
            self.status_var.set(f"Error loading database: {str(e)}")
            messagebox.showerror("Database Error", f"An error occurred loading the database:\n\n{str(e)}")
    
    def apply_filters(self):
        """Apply filters to the dataset and update the display"""
        if self.full_dataset.empty:
            return
            
        app_logger.debug("Applying filters to invoice data")
        
        try:
            # Start with the full dataset
            df = self.full_dataset.copy()
            
            # Apply status filters
            status_filters = []
            if self.show_auto_approved.get():
                status_filters.append("Auto-Approved")
            if self.show_needs_review.get():
                status_filters.append("Needs Review")
            if self.show_manual.get():
                status_filters.append("Manual Processing Required")
            
            if status_filters:
                df = df[df['status'].isin(status_filters)]
            
            # Apply search if provided
            search_text = self.search_var.get().strip().lower()
            if search_text:
                search_field = self.search_in.get()
                
                if search_field == "All Fields":
                    # Search in all string columns
                    mask = False
                    for col in ['invoice_id', 'vendor', 'date', 'status']:
                        if col in df.columns:
                            mask = mask | df[col].astype(str).str.lower().str.contains(search_text, na=False)
                    df = df[mask]
                elif search_field == "Invoice #":
                    df = df[df['invoice_id'].astype(str).str.lower().str.contains(search_text, na=False)]
                elif search_field == "Vendor":
                    df = df[df['vendor'].astype(str).str.lower().str.contains(search_text, na=False)]
                elif search_field == "Date":
                    df = df[df['date'].astype(str).str.lower().str.contains(search_text, na=False)]
                elif search_field == "Status":
                    df = df[df['status'].astype(str).str.lower().str.contains(search_text, na=False)]
            
            # Store the filtered dataset
            self.filtered_dataset = df
            
            # Sort the data
            if self.sort_column in df.columns:
                df = df.sort_values(by=self.sort_column, ascending=not self.sort_reverse)
            
            # Clear existing data
            for item in self.invoice_table.get_children():
                self.invoice_table.delete(item)
            
            # Add filtered data to table
            for _, row in df.iterrows():
                confidence = row.get('confidence_score', 0) * 100
                
                # Format amount with currency symbol
                try:
                    amount = float(row['amount'])
                    amount_str = f"${amount:.2f}"
                except (ValueError, TypeError):
                    amount_str = row['amount']
                
                # Insert into table
                self.invoice_table.insert('', tk.END, values=(
                    row['invoice_id'],
                    row['vendor'],
                    row['date'],
                    amount_str,
                    row['status'],
                    f"{confidence:.1f}%",
                    row['processed_date']
                ))
            
            # Update status bar
            self.status_var.set(f"{len(df)} invoices displayed (filtered from {len(self.full_dataset)})")
            app_logger.debug(f"Applied filters: {len(df)} invoices displayed")
            
        except Exception as e:
            app_logger.error(f"Error applying filters: {str(e)}")
            self.status_var.set(f"Error applying filters: {str(e)}")
    
    def search_invoices(self):
        """Apply the search filter"""
        app_logger.debug(f"Searching invoices with text: {self.search_var.get()}")
        self.apply_filters()
    
    def clear_search(self):
        """Clear the search field and refresh the view"""
        self.search_var.set("")
        self.apply_filters()
    
    def view_invoice(self):
        """View details of the selected invoice from the database"""
        selected_item = self.invoice_table.selection()
        if not selected_item:
            app_logger.warning("No invoice selected for viewing")
            self.status_var.set("No invoice selected. Please select an invoice from the table.")
            messagebox.showwarning("No Selection", "Please select an invoice from the table first.")
            return
        
        # Get the invoice_id of the selected item
        invoice_id = self.invoice_table.item(selected_item[0], 'values')[0]
        app_logger.info(f"Viewing invoice details: {invoice_id}")
        
        try:
            # Get the invoice data
            invoice_data = get_invoice_by_id(invoice_id)
            
            if invoice_data:
                # Create a new window to display details
                details_window = tk.Toplevel(self.parent.winfo_toplevel())
                details_window.title(f"Invoice Details: {invoice_id}")
                details_window.geometry("800x600")
                
                # Add metadata at the top
                metadata_frame = ttk.Frame(details_window, padding=10)
                metadata_frame.pack(fill=tk.X)
                
                # Invoice ID and vendor
                ttk.Label(metadata_frame, text=f"Invoice #: {invoice_id}", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(metadata_frame, text=f"Vendor: {invoice_data['vendor']['name']}", font=("Arial", 12)).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
                
                # Date and amount
                date = invoice_data['metadata'].get('date', 'Unknown')
                amount = invoice_data['metadata'].get('total_amount', invoice_data['totals'].get('total', 0))
                ttk.Label(metadata_frame, text=f"Date: {date}").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(metadata_frame, text=f"Amount: ${float(amount):.2f}").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
                
                # Status and confidence
                status = invoice_data['validation']['status']
                confidence = invoice_data['validation']['overall_confidence'] * 100
                ttk.Label(metadata_frame, text=f"Status: {status}").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(metadata_frame, text=f"Confidence: {confidence:.1f}%").grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
                
                # Create notebook for different views
                notebook = ttk.Notebook(details_window)
                notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # JSON Data tab
                json_frame = ttk.Frame(notebook)
                notebook.add(json_frame, text="JSON Data")
                
                # JSON text view
                json_text = tk.Text(json_frame, wrap=tk.WORD)
                json_scrollbar = ttk.Scrollbar(json_frame, command=json_text.yview)
                json_text.configure(yscrollcommand=json_scrollbar.set)
                
                json_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                json_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Insert the formatted JSON data
                json_text.insert(tk.END, json.dumps(invoice_data, indent=2))
                
                # Items tab if there are line items
                if invoice_data['items']:
                    items_frame = ttk.Frame(notebook)
                    notebook.add(items_frame, text="Line Items")
                    
                    # Create treeview for items
                    columns = ('description', 'quantity', 'unit_price', 'total')
                    items_table = ttk.Treeview(items_frame, columns=columns, show='headings')
                    
                    # Define headings
                    items_table.heading('description', text='Description')
                    items_table.heading('quantity', text='Quantity')
                    items_table.heading('unit_price', text='Unit Price')
                    items_table.heading('total', text='Total')
                    
                    # Define columns
                    items_table.column('description', width=300)
                    items_table.column('quantity', width=80)
                    items_table.column('unit_price', width=100)
                    items_table.column('total', width=100)
                    
                    # Add scrollbar
                    items_scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=items_table.yview)
                    items_table.configure(yscrollcommand=items_scrollbar.set)
                    
                    # Pack table and scrollbar
                    items_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    items_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # Add items to table
                    for item in invoice_data['items']:
                        items_table.insert('', tk.END, values=(
                            item['description'],
                            item['quantity'],
                            f"${item['unit_price']:.2f}",
                            f"${item['total']:.2f}"
                        ))
                
                # Validation tab
                validation_frame = ttk.Frame(notebook)
                notebook.add(validation_frame, text="Validation")
                
                # Validation results
                validation_text = tk.Text(validation_frame, wrap=tk.WORD)
                validation_scrollbar = ttk.Scrollbar(validation_frame, command=validation_text.yview)
                validation_text.configure(yscrollcommand=validation_scrollbar.set)
                
                validation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                validation_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Insert validation information
                validation_text.insert(tk.END, f"Status: {status}\n")
                validation_text.insert(tk.END, f"Overall Confidence: {confidence:.1f}%\n\n")
                
                if invoice_data['validation']['warnings']:
                    validation_text.insert(tk.END, "Warnings:\n")
                    for warning in invoice_data['validation']['warnings']:
                        validation_text.insert(tk.END, f"- {warning}\n")
                else:
                    validation_text.insert(tk.END, "No warnings or errors detected.\n")
                
                # Buttons at the bottom
                button_frame = ttk.Frame(details_window, padding=10)
                button_frame.pack(fill=tk.X, side=tk.BOTTOM)
                
                ttk.Button(button_frame, text="Close", command=details_window.destroy).pack(side=tk.RIGHT, padx=5)
                ttk.Button(button_frame, text="Export", command=lambda: self._export_invoice(invoice_data)).pack(side=tk.RIGHT, padx=5)
            else:
                app_logger.warning(f"Invoice {invoice_id} not found")
                messagebox.showwarning("Not Found", f"Invoice {invoice_id} could not be found in the database.")
        
        except Exception as e:
            app_logger.error(f"Error viewing invoice details: {str(e)}")
            self.status_var.set(f"Error viewing invoice details: {str(e)}")
            messagebox.showerror("View Error", f"An error occurred viewing invoice details:\n\n{str(e)}")
    
    def export_selected(self):
        """Export the selected invoice to a file"""
        selected_item = self.invoice_table.selection()
        if not selected_item:
            app_logger.warning("No invoice selected for export")
            self.status_var.set("No invoice selected. Please select an invoice from the table.")
            messagebox.showwarning("No Selection", "Please select an invoice from the table first.")
            return
        
        # Get the invoice_id of the selected item
        invoice_id = self.invoice_table.item(selected_item[0], 'values')[0]
        app_logger.info(f"Exporting invoice: {invoice_id}")
        
        try:
            # Get the invoice data
            invoice_data = get_invoice_by_id(invoice_id)
            
            if invoice_data:
                self._export_invoice(invoice_data)
            else:
                app_logger.warning(f"Invoice {invoice_id} not found for export")
                messagebox.showwarning("Not Found", f"Invoice {invoice_id} could not be found in the database.")
        
        except Exception as e:
            app_logger.error(f"Error exporting invoice: {str(e)}")
            self.status_var.set(f"Error exporting invoice: {str(e)}")
            messagebox.showerror("Export Error", f"An error occurred exporting the invoice:\n\n{str(e)}")
    
    def _export_invoice(self, invoice_data):
        """
        Export an invoice to a file
        
        Args:
            invoice_data (dict): Invoice data to export
        """
        # Ask for export format
        export_format = tk.StringVar(value="csv")
        
        dialog = tk.Toplevel(self.parent.winfo_toplevel())
        dialog.title("Export Options")
        dialog.geometry("300x200")
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select export format:").pack(pady=10)
        
        ttk.Radiobutton(dialog, text="CSV", variable=export_format, value="csv").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(dialog, text="JSON", variable=export_format, value="json").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(dialog, text="Excel", variable=export_format, value="excel").pack(anchor=tk.W, padx=20)
        
        # Accounting system export option
        ttk.Label(dialog, text="Export for accounting system:").pack(pady=(10,0), anchor=tk.W, padx=10)
        accounting_system = tk.StringVar(value="generic")
        accounting_combo = ttk.Combobox(dialog, textvariable=accounting_system, 
                                        values=["generic", "quickbooks", "xero", "sage"], 
                                        state="readonly", width=15)
        accounting_combo.pack(pady=5, padx=20, anchor=tk.W)
        
        def do_export():
            format_val = export_format.get()
            accounting_val = accounting_system.get()
            
            app_logger.info(f"Exporting invoice to {format_val} format")
            
            if accounting_val != "generic" and accounting_val != "":
                # Export to accounting format
                filename = export_to_accounting_system(invoice_data, accounting_val)
                export_type = f"{accounting_val.capitalize()} format"
            else:
                # Regular export
                from invoice_processor.utils.export_utils import export_to_csv, export_to_json, export_to_excel
                
                if format_val == "csv":
                    filename = export_to_csv(invoice_data)
                elif format_val == "json":
                    filename = export_to_json(invoice_data)
                elif format_val == "excel":
                    filename = export_to_excel(invoice_data)
                else:
                    filename = None
                
                export_type = format_val.upper()
            
            if filename:
                self.status_var.set(f"Invoice data exported to {filename}")
                app_logger.info(f"Invoice exported to {filename}")
                messagebox.showinfo("Export Successful", f"Invoice data exported in {export_type} to:\n{filename}")
            else:
                self.status_var.set("Error exporting invoice data")
                app_logger.error("Failed to export invoice data")
                messagebox.showerror("Export Error", "An error occurred while exporting the invoice data.")
            
            dialog.destroy()
        
        ttk.Button(dialog, text="Export", command=do_export).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)
    
    def delete_invoice(self):
        """Delete the selected invoice from the database"""
        selected_item = self.invoice_table.selection()
        if not selected_item:
            app_logger.warning("No invoice selected for deletion")
            messagebox.showwarning("No Selection", "Please select an invoice from the table first.")
            return
        
        # Get the invoice_id of the selected item
        invoice_id = self.invoice_table.item(selected_item[0], 'values')[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete invoice {invoice_id}?"):
            return
        
        app_logger.info(f"Deleting invoice: {invoice_id}")
        
        try:
            # For this demonstration, we'll simply remove it from the table
            # In a real application, you would implement the actual database deletion
            self.invoice_table.delete(selected_item)
            
            # Update status
            self.status_var.set(f"Invoice {invoice_id} deleted")
            app_logger.info(f"Invoice {invoice_id} deleted")
            
            # Refresh the database display
            self.load_database()
            
        except Exception as e:
            app_logger.error(f"Error deleting invoice: {str(e)}")
            self.status_var.set(f"Error deleting invoice: {str(e)}")
            messagebox.showerror("Delete Error", f"An error occurred deleting the invoice:\n\n{str(e)}")
    
    def _sort_by_column(self, column):
        """
        Sort the table by the specified column
        
        Args:
            column (str): Column name to sort by
        """
        app_logger.debug(f"Sorting by column: {column}")
        
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            # New column, default to ascending
            self.sort_column = column
            self.sort_reverse = False
        
        # Apply filters with new sort
        self.apply_filters()
    
    def _show_context_menu(self, event):
        """
        Show context menu on right-click
        
        Args:
            event: Right-click event
        """
        try:
            # Select the item under the mouse
            item = self.invoice_table.identify_row(event.y)
            if item:
                self.invoice_table.selection_set(item)
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()