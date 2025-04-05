"""
Process tab for invoice processing.

This module defines the UI components for the invoice processing tab.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os

from PIL import Image, ImageTk

from invoice_processor.logger import app_logger
from invoice_processor.core.document_processor import extract_text_from_invoice, preview_invoice
from invoice_processor.core.data_extractor import parse_invoice_text
from invoice_processor.core.database import save_to_database, export_to_accounting_system

class ProcessTab:
    """Process tab for invoice processing"""
    
    def __init__(self, parent, vendor_classifier):
        """
        Initialize the process tab
        
        Args:
            parent (ttk.Frame): Parent frame
            vendor_classifier (VendorClassifier): Trained vendor classifier
        """
        self.parent = parent
        self.vendor_classifier = vendor_classifier
        self.database_tab = None  # Will be set later
        
        # Variables for storing current invoice data
        self.current_pdf_path = None
        self.current_extraction_result = None
        self.current_invoice_data = None
        self.current_images = []
        
        # Setup UI components
        self._setup_ui()
    
    def set_database_tab(self, database_tab):
        """
        Set reference to database tab for data sharing
        
        Args:
            database_tab (DatabaseTab): Database tab instance
        """
        self.database_tab = database_tab
    
    def _setup_ui(self):
        """Set up UI components"""
        # Create frames
        self.top_frame = ttk.Frame(self.parent, padding=10)
        self.top_frame.pack(fill=tk.X)
        
        self.middle_frame = ttk.Frame(self.parent, padding=10)
        self.middle_frame.pack(fill=tk.BOTH, expand=True)
        
        self.bottom_frame = ttk.Frame(self.parent, padding=10)
        self.bottom_frame.pack(fill=tk.X)
        
        # Top frame controls
        ttk.Label(self.top_frame, text="Invoice Processing", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.top_frame, text="Select Invoice PDF", command=self.select_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Process Invoice", command=self.process_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Save to Database", command=self.save_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Export Data", command=self.export_data).pack(side=tk.LEFT, padx=5)
        
        # Middle frame - split into image preview and data display
        self.left_frame = ttk.Frame(self.middle_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_frame = ttk.Frame(self.middle_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Image preview area
        ttk.Label(self.left_frame, text="Document Preview", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        self.image_frame = ttk.Frame(self.left_frame, borderwidth=1, relief=tk.SUNKEN)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Extracted data display
        ttk.Label(self.right_frame, text="Extracted Data", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # Create a frame for the results
        result_frame = ttk.Frame(self.right_frame)
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
        status_bar = ttk.Label(self.bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X)
        
        # Confidence meter
        self.confidence_frame = ttk.Frame(self.bottom_frame)
        self.confidence_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.confidence_frame, text="Confidence:").pack(side=tk.LEFT, padx=5)
        self.confidence_var = tk.DoubleVar()
        self.confidence_var.set(0.0)
        self.confidence_meter = ttk.Progressbar(self.confidence_frame, variable=self.confidence_var, 
                                               maximum=100, length=200, mode='determinate')
        self.confidence_meter.pack(side=tk.LEFT, padx=5)
        
        self.confidence_label = ttk.Label(self.confidence_frame, text="0%")
        self.confidence_label.pack(side=tk.LEFT, padx=5)
    
    def select_invoice(self):
        """Open file dialog to select an invoice PDF"""
        app_logger.debug("Opening file dialog to select invoice PDF")
        
        filetypes = (("PDF files", "*.pdf"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(
            title="Select Invoice PDF",
            filetypes=filetypes
        )
        
        if filepath:
            self.current_pdf_path = filepath
            self.status_var.set(f"Selected: {os.path.basename(filepath)}")
            app_logger.info(f"Selected invoice PDF: {filepath}")
            
            # Clear previous results
            self.result_text.delete(1.0, tk.END)
            self.current_extraction_result = None
            self.current_invoice_data = None
            
            # Show first page preview
            self._display_preview(filepath)
        else:
            app_logger.debug("No file selected")
    
    def _display_preview(self, pdf_path):
        """
        Display a preview of the first page of the PDF
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        app_logger.debug(f"Generating preview for {pdf_path}")
        
        try:
            # Get preview image
            img = preview_invoice(pdf_path)
            
            if img:
                # Resize to fit the display area
                img.thumbnail((400, 550))
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Update image label
                self.image_label.config(image=photo)
                self.image_label.image = photo  # Keep a reference to prevent garbage collection
                app_logger.debug("Preview displayed successfully")
            else:
                app_logger.warning("Failed to generate preview image")
                self.image_label.config(image=None)
                self.image_label.image = None
        
        except Exception as e:
            app_logger.error(f"Error displaying PDF preview: {str(e)}")
            self.status_var.set(f"Error previewing PDF: {str(e)}")
    
    def process_invoice(self):
        """Process the selected invoice PDF"""
        if not self.current_pdf_path:
            app_logger.warning("No invoice selected")
            self.status_var.set("No invoice selected. Please select an invoice PDF first.")
            messagebox.showwarning("No Invoice Selected", "Please select an invoice PDF first.")
            return
        
        self.status_var.set("Processing invoice... Please wait.")
        self.parent.update()  # Update the UI
        app_logger.info(f"Processing invoice: {self.current_pdf_path}")
        
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
            app_logger.info(f"Invoice processed successfully. Status: {status}")
            
        except Exception as e:
            app_logger.error(f"Error processing invoice: {str(e)}")
            self.status_var.set(f"Error processing invoice: {str(e)}")
            messagebox.showerror("Processing Error", f"An error occurred while processing the invoice:\n\n{str(e)}")
    
    def save_invoice(self):
        """Save the processed invoice data to the database"""
        if not self.current_invoice_data:
            app_logger.warning("No invoice data to save")
            self.status_var.set("No invoice data to save. Please process an invoice first.")
            messagebox.showwarning("No Data", "No invoice data to save. Please process an invoice first.")
            return
        
        app_logger.info("Saving invoice to database")
        if save_to_database(self.current_invoice_data, self.current_pdf_path):
            self.status_var.set("Invoice saved to database successfully.")
            app_logger.info("Invoice saved successfully")
            
            # Refresh the database display if available
            if self.database_tab:
                self.database_tab.load_database()
                
            # Show success message
            messagebox.showinfo("Success", "Invoice saved to database successfully.")
        else:
            self.status_var.set("Error saving invoice to database.")
            app_logger.error("Failed to save invoice to database")
            messagebox.showerror("Save Error", "An error occurred while saving the invoice to the database.")
    
    def export_data(self):
        """Export the processed invoice data to a file"""
        if not self.current_invoice_data:
            app_logger.warning("No invoice data to export")
            self.status_var.set("No invoice data to export. Please process an invoice first.")
            messagebox.showwarning("No Data", "No invoice data to export. Please process an invoice first.")
            return
        
        app_logger.info("Opening export dialog")
        # Ask for export format
        export_format = tk.StringVar(value="csv")
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Export Options")
        dialog.geometry("300x150")
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select export format:").pack(pady=10)
        
        ttk.Radiobutton(dialog, text="CSV", variable=export_format, value="csv").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(dialog, text="JSON", variable=export_format, value="json").pack(anchor=tk.W, padx=20)
        
        def do_export():
            format_val = export_format.get()
            app_logger.info(f"Exporting invoice data to {format_val} format")
            filename = export_to_accounting_system(self.current_invoice_data, format_val)
            if filename:
                self.status_var.set(f"Invoice data exported to {filename}")
                app_logger.info(f"Invoice data exported to {filename}")
                messagebox.showinfo("Export Successful", f"Invoice data exported to:\n{filename}")
            else:
                self.status_var.set("Error exporting invoice data")
                app_logger.error("Failed to export invoice data")
                messagebox.showerror("Export Error", "An error occurred while exporting the invoice data.")
            dialog.destroy()
        
        ttk.Button(dialog, text="Export", command=do_export).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)