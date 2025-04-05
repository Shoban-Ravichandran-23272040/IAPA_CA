"""
Main entry point for the Intelligent Invoice Processor application.

This module initializes the application and starts the UI.
"""

import tkinter as tk
import os
import sys

from invoice_processor.logger import app_logger
from invoice_processor.config import UI_TITLE, UI_WINDOW_SIZE
from invoice_processor.core.database import initialize_database
from invoice_processor.core.ml_classifier import VendorClassifier, generate_training_data
from invoice_processor.ui.app import InvoiceProcessorApp

def initialize_application():
    """
    Initialize the application components
    
    Returns:
        VendorClassifier: Initialized vendor classifier
    """
    app_logger.info("Initializing application")
    
    # Initialize database
    if initialize_database():
        app_logger.info("Database initialized successfully")
    else:
        app_logger.error("Failed to initialize database")
    
    # Initialize vendor classifier
    vendor_classifier = VendorClassifier()
    
    # Try to load existing model, or train a new one
    if vendor_classifier.load_model():
        app_logger.info("Vendor classification model loaded successfully")
    else:
        app_logger.info("Training new vendor classification model")
        training_data = generate_training_data()
        vendor_classifier.train(training_data)
        vendor_classifier.save_model()
        app_logger.info("Vendor classification model trained and saved")
    
    return vendor_classifier

def main():
    """
    Main entry point for the application
    """
    app_logger.info("Starting Intelligent Invoice Processor")
    
    # Initialize application components
    vendor_classifier = initialize_application()
    
    # Create main window
    root = tk.Tk()
    root.title(UI_TITLE)
    root.geometry(UI_WINDOW_SIZE)
    
    # Create application
    app = InvoiceProcessorApp(root, vendor_classifier)
    
    # Run the application
    app_logger.info("Starting main application loop")
    root.mainloop()
    
    app_logger.info("Application closed")

if __name__ == "__main__":
    main()