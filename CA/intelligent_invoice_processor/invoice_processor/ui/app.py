"""
Main application window for the Invoice Processor.

This module defines the main application window and 
integrates the different UI components.
"""

import tkinter as tk
from tkinter import ttk

from invoice_processor.logger import app_logger
from invoice_processor.ui.process_tab import ProcessTab
from invoice_processor.ui.database_tab import DatabaseTab
from invoice_processor.ui.analytics_tab import AnalyticsTab

class InvoiceProcessorApp:
    """Main application window for the Invoice Processor"""
    
    def __init__(self, root, vendor_classifier):
        """
        Initialize the application
        
        Args:
            root (tk.Tk): Root Tkinter window
            vendor_classifier (VendorClassifier): Trained vendor classifier
        """
        self.root = root
        self.vendor_classifier = vendor_classifier
        
        app_logger.debug("Setting up main application window")
        
        # Configure style
        self._setup_style()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.tab_control = ttk.Notebook(self.main_frame)
        
        # Create tab frames
        self.process_tab_frame = ttk.Frame(self.tab_control)
        self.database_tab_frame = ttk.Frame(self.tab_control)
        self.analytics_tab_frame = ttk.Frame(self.tab_control)
        
        # Add tab frames to notebook
        self.tab_control.add(self.process_tab_frame, text="Process Invoice")
        self.tab_control.add(self.database_tab_frame, text="Invoice Database")
        self.tab_control.add(self.analytics_tab_frame, text="Analytics")
        self.tab_control.pack(expand=True, fill=tk.BOTH)
        
        # Initialize tab content
        self._setup_tabs()
        
        # Set up menu
        self._setup_menu()
        
        # Bind events
        self._bind_events()
        
        app_logger.debug("Application setup complete")
    
    def _setup_style(self):
        """Configure application style"""
        self.style = ttk.Style()
        
        # Check if the theme is available
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
        
        # Configure styles
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TNotebook', background='#f5f5f5')
        self.style.configure('TNotebook.Tab', padding=[10, 2], background='#e0e0e0')
        self.style.map('TNotebook.Tab', background=[('selected', '#f0f0f0')])
        self.style.configure('TButton', padding=6)
    
    def _setup_tabs(self):
        """Initialize tab content"""
        # Process tab
        self.process_tab = ProcessTab(self.process_tab_frame, self.vendor_classifier)
        
        # Database tab
        self.database_tab = DatabaseTab(self.database_tab_frame)
        
        # Analytics tab
        self.analytics_tab = AnalyticsTab(self.analytics_tab_frame)
        
        # Connect tabs for data sharing
        self.process_tab.set_database_tab(self.database_tab)
        self.database_tab.set_process_tab(self.process_tab)
    
    def _setup_menu(self):
        """Set up application menu"""
        self.menu_bar = tk.Menu(self.root)
        
        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Select Invoice", command=self.process_tab.select_invoice)
        self.file_menu.add_command(label="Export Data", command=self.process_tab.export_data)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        
        # Tools menu
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="Refresh Database", command=self.database_tab.load_database)
        self.tools_menu.add_command(label="Generate Analytics", command=self.analytics_tab.generate_analytics)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Retrain Classifier", command=self._retrain_classifier)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        
        # Help menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        
        self.root.config(menu=self.menu_bar)
    
    def _bind_events(self):
        """Bind event handlers"""
        # Handle tab change
        self.tab_control.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_tab_changed(self, event):
        """
        Handle tab change event
        
        Args:
            event: Tab change event
        """
        current_tab = self.tab_control.index(self.tab_control.select())
        
        # If changing to Database tab, refresh data
        if current_tab == 1:  # Database tab
            self.database_tab.load_database()
        
        # If changing to Analytics tab, regenerate analytics
        elif current_tab == 2:  # Analytics tab
            self.analytics_tab.check_data_availability()
    
    def _on_close(self):
        """Handle window close event"""
        app_logger.info("Application closing")
        self.root.destroy()
    
    def _retrain_classifier(self):
        """Retrain the vendor classifier"""
        from invoice_processor.core.ml_classifier import generate_training_data
        
        app_logger.info("Retraining vendor classifier")
        training_data = generate_training_data()
        self.vendor_classifier.train(training_data)
        self.vendor_classifier.save_model()
        
        # Show success message
        tk.messagebox.showinfo("Training Complete", "Vendor classifier has been retrained successfully.")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """
Intelligent Invoice Processor

Version: 0.1.0

A powerful OCR and machine learning-based solution
for automating accounts payable invoice processing.

© 2025 Your Name
        """
        tk.messagebox.showinfo("About", about_text)