"""
Analytics tab for invoice processing visualization.

This module defines the UI components for the analytics tab.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import os

from invoice_processor.logger import app_logger
from invoice_processor.core.database import get_all_invoices

class AnalyticsTab:
    """Analytics tab for invoice processing visualization"""
    
    def __init__(self, parent):
        """
        Initialize the analytics tab
        
        Args:
            parent (ttk.Frame): Parent frame
        """
        self.parent = parent
        
        # Initialize chart references
        self.vendor_canvas = None
        self.time_canvas = None
        self.performance_canvas = None
        self.confidence_canvas = None
        
        # Setup UI components
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up UI components"""
        # Create frames for analytics content
        self.top_frame = ttk.Frame(self.parent, padding=10)
        self.top_frame.pack(fill=tk.X)
        
        self.content_frame = ttk.Frame(self.parent, padding=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Analytics title and controls
        ttk.Label(self.top_frame, text="Invoice Analytics", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Generate Reports", command=self.generate_analytics).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Export Charts", command=self.export_charts).pack(side=tk.LEFT, padx=5)
        
        # Time filter for analytics
        self.filter_frame = ttk.Frame(self.top_frame)
        self.filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(self.filter_frame, text="Time Range:").pack(side=tk.LEFT, padx=5)
        self.time_filter = tk.StringVar(value="All Time")
        time_options = ttk.Combobox(self.filter_frame, textvariable=self.time_filter, 
                                   values=["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"], 
                                   state="readonly", width=15)
        time_options.pack(side=tk.LEFT, padx=5)
        time_options.bind("<<ComboboxSelected>>", lambda e: self.generate_analytics())
        
        # Create notebook for different analytics views
        self.analytics_notebook = ttk.Notebook(self.content_frame)
        
        # Create tabs for different analytics
        self.vendor_tab = ttk.Frame(self.analytics_notebook)
        self.time_tab = ttk.Frame(self.analytics_notebook)
        self.performance_tab = ttk.Frame(self.analytics_notebook)
        self.confidence_tab = ttk.Frame(self.analytics_notebook)
        
        self.analytics_notebook.add(self.vendor_tab, text="Vendor Analysis")
        self.analytics_notebook.add(self.time_tab, text="Time Analysis")
        self.analytics_notebook.add(self.performance_tab, text="Performance Metrics")
        self.analytics_notebook.add(self.confidence_tab, text="Confidence Analysis")
        
        self.analytics_notebook.pack(expand=True, fill=tk.BOTH)
        
        # Vendor Analysis Tab
        self.vendor_frame = ttk.Frame(self.vendor_tab, padding=10)
        self.vendor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Time Analysis Tab
        self.time_frame = ttk.Frame(self.time_tab, padding=10)
        self.time_frame.pack(fill=tk.BOTH, expand=True)
        
        # Performance Metrics Tab
        self.perf_frame = ttk.Frame(self.performance_tab, padding=10)
        self.perf_frame.pack(fill=tk.BOTH, expand=True)
        
        # Confidence Analysis Tab
        self.confidence_frame = ttk.Frame(self.confidence_tab, padding=10)
        self.confidence_frame.pack(fill=tk.BOTH, expand=True)
        
        # No data message
        self.no_data_label = ttk.Label(self.content_frame, 
                                       text="No invoice data available. Process some invoices first.",
                                       font=("Arial", 12))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Analytics not generated")
        status_bar = ttk.Label(self.parent, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
    
    def check_data_availability(self):
        """Check if data is available and show appropriate UI"""
        app_logger.debug("Checking data availability for analytics")
        
        try:
            df = get_all_invoices()
            
            if df.empty:
                app_logger.debug("No invoice data available for analytics")
                self.analytics_notebook.pack_forget()
                self.no_data_label.pack(fill=tk.BOTH, expand=True)
                self.status_var.set("No invoice data available for analytics")
                return False
            else:
                app_logger.debug(f"Found {len(df)} invoices for analytics")
                self.no_data_label.pack_forget()
                self.analytics_notebook.pack(expand=True, fill=tk.BOTH)
                return True
                
        except Exception as e:
            app_logger.error(f"Error checking data availability: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            return False
    
    def generate_analytics(self):
        """Generate analytics visualizations"""
        app_logger.info("Generating analytics visualizations")
        
        if not self.check_data_availability():
            return
        
        try:
            # Get all invoices
            df = get_all_invoices()
            
            # Apply time filter
            df = self._apply_time_filter(df)
            
            if df.empty:
                app_logger.warning("No data available after filtering")
                self.status_var.set("No data available for the selected time period")
                return
            
            # Generate vendor analysis chart
            self._generate_vendor_chart(df)
            
            # Generate time analysis chart
            self._generate_time_chart(df)
            
            # Generate performance metrics
            self._generate_performance_metrics(df)
            
            # Generate confidence analysis
            self._generate_confidence_analysis(df)
            
            self.status_var.set(f"Analytics generated successfully with {len(df)} invoices")
            app_logger.info("Analytics generated successfully")
            
        except Exception as e:
            app_logger.error(f"Error generating analytics: {str(e)}")
            self.status_var.set(f"Error generating analytics: {str(e)}")
            messagebox.showerror("Analytics Error", f"An error occurred generating analytics:\n\n{str(e)}")
    
    def _apply_time_filter(self, df):
        """
        Apply time filter to dataframe
        
        Args:
            df (pandas.DataFrame): Invoice dataframe
            
        Returns:
            pandas.DataFrame: Filtered dataframe
        """
        if 'processed_date' not in df.columns or df.empty:
            return df
            
        filter_value = self.time_filter.get()
        
        if filter_value == "All Time":
            return df
            
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_dtype(df['processed_date']):
            df['processed_date'] = pd.to_datetime(df['processed_date'], errors='coerce')
        
        # Get current date
        now = datetime.now()
        
        # Apply filter
        if filter_value == "Last 7 Days":
            start_date = now - timedelta(days=7)
            return df[df['processed_date'] >= start_date]
            
        elif filter_value == "Last 30 Days":
            start_date = now - timedelta(days=30)
            return df[df['processed_date'] >= start_date]
            
        elif filter_value == "Last 90 Days":
            start_date = now - timedelta(days=90)
            return df[df['processed_date'] >= start_date]
            
        return df
    
    def _generate_vendor_chart(self, df):
        """
        Generate vendor analysis chart
        
        Args:
            df (pandas.DataFrame): Invoice dataframe
        """
        app_logger.debug("Generating vendor analysis chart")
        
        # Clear previous chart
        for widget in self.vendor_frame.winfo_children():
            widget.destroy()
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Group by vendor and count invoices
        if 'vendor' in df.columns:
            vendor_counts = df['vendor'].value_counts()
            
            if vendor_counts.empty:
                # Show message if no data
                ttk.Label(self.vendor_frame, text="No vendor data available").pack(pady=20)
                return
                
            # Limit to top 10 vendors if there are many
            if len(vendor_counts) > 10:
                vendor_counts = vendor_counts.head(10)
                ax.set_title('Top 10 Vendors by Invoice Count')
            else:
                ax.set_title('Invoice Count by Vendor')
            
            # Create bar chart
            vendor_counts.plot(kind='bar', ax=ax)
            ax.set_xlabel('Vendor')
            ax.set_ylabel('Number of Invoices')
            
            # Rotate x-axis labels for better readability
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Add value labels on bars
            for i, v in enumerate(vendor_counts):
                ax.text(i, v + 0.1, str(v), ha='center')
            
            # Adjust layout
            fig.tight_layout()
            
            # Embed in canvas
            canvas = FigureCanvasTkAgg(fig, self.vendor_frame)
            self.vendor_canvas = canvas
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(self.vendor_frame, text="Vendor data not available").pack(pady=20)
    
    def _generate_time_chart(self, df):
        """
        Generate time analysis chart
        
        Args:
            df (pandas.DataFrame): Invoice dataframe
        """
        app_logger.debug("Generating time analysis chart")
        
        # Clear previous chart
        for widget in self.time_frame.winfo_children():
            widget.destroy()
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Convert date to datetime and sort
        try:
            if 'processed_date' in df.columns:
                # Convert to datetime if not already
                if not pd.api.types.is_datetime64_dtype(df['processed_date']):
                    df['processed_date'] = pd.to_datetime(df['processed_date'], errors='coerce')
                
                # Drop rows with invalid dates
                df = df.dropna(subset=['processed_date'])
                
                if df.empty:
                    ttk.Label(self.time_frame, text="No valid date data available").pack(pady=20)
                    return
                
                # Sort by date
                df = df.sort_values('processed_date')
                
                # Group by day and count
                df['date'] = df['processed_date'].dt.date
                daily_counts = df.groupby('date').size()
                
                # Plot time series
                daily_counts.plot(ax=ax)
                ax.set_title('Invoices Processed Over Time')
                ax.set_xlabel('Date')
                ax.set_ylabel('Number of Invoices')
                
                # Format x-axis dates
                fig.autofmt_xdate()
                
                # Add grid for better readability
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # Embed in canvas
                canvas = FigureCanvasTkAgg(fig, self.time_frame)
                self.time_canvas = canvas
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            else:
                ttk.Label(self.time_frame, text="Date data not available").pack(pady=20)
                
        except Exception as e:
            app_logger.error(f"Error generating time chart: {str(e)}")
            ttk.Label(self.time_frame, text=f"Error generating chart: {str(e)}").pack(pady=20)
    
    def _generate_performance_metrics(self, df):
        """
        Generate performance metrics visualization
        
        Args:
            df (pandas.DataFrame): Invoice dataframe
        """
        app_logger.debug("Generating performance metrics")
        
        # Clear previous content
        for widget in self.perf_frame.winfo_children():
            widget.destroy()
        
        if 'status' not in df.columns or df.empty:
            ttk.Label(self.perf_frame, text="Status data not available").pack(pady=20)
            return
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Calculate metrics
        total_invoices = len(df)
        
        # Status counts
        status_counts = {
            'Auto-Approved': len(df[df['status'] == 'Auto-Approved']),
            'Needs Review': len(df[df['status'] == 'Needs Review']),
            'Manual Processing Required': len(df[df['status'] == 'Manual Processing Required'])
        }
        
        # Create pie chart
        labels = list(status_counts.keys())
        sizes = list(status_counts.values())
        
        # Only include non-zero values
        non_zero_labels = []
        non_zero_sizes = []
        for label, size in zip(labels, sizes):
            if size > 0:
                non_zero_labels.append(label)
                non_zero_sizes.append(size)
        
        if not non_zero_sizes:
            ttk.Label(self.perf_frame, text="No status data available").pack(pady=20)
            return
        
        colors = ['#4CAF50', '#FFC107', '#F44336']
        explode = (0.1, 0, 0)  # Explode the 1st slice (Auto-Approved)
        
        ax.pie(non_zero_sizes, explode=explode[:len(non_zero_sizes)], labels=non_zero_labels, 
               colors=colors[:len(non_zero_sizes)], autopct='%1.1f%%', startangle=90, shadow=True)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        ax.set_title('Invoice Processing Performance')
        
        # Add legend with counts
        legend_labels = [f"{label} ({count})" for label, count in zip(non_zero_labels, non_zero_sizes)]
        ax.legend(legend_labels, loc="best")
        
        # Embed in canvas
        canvas = FigureCanvasTkAgg(fig, self.perf_frame)
        self.performance_canvas = canvas
        canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add additional metrics in a frame
        metrics_frame = ttk.Frame(self.perf_frame)
        metrics_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        ttk.Label(metrics_frame, text="Summary Metrics", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        
        # Total invoices
        ttk.Label(metrics_frame, text=f"Total Invoices: {total_invoices}").pack(anchor=tk.W, pady=2)
        
        # Auto-approval rate
        auto_rate = (status_counts['Auto-Approved'] / total_invoices * 100) if total_invoices > 0 else 0
        ttk.Label(metrics_frame, text=f"Auto-Approval Rate: {auto_rate:.1f}%").pack(anchor=tk.W, pady=2)
        
        # Manual processing rate
        manual_rate = (status_counts['Manual Processing Required'] / total_invoices * 100) if total_invoices > 0 else 0
        ttk.Label(metrics_frame, text=f"Manual Processing Rate: {manual_rate:.1f}%").pack(anchor=tk.W, pady=2)
        
        # Average confidence (if available)
        if 'confidence_score' in df.columns:
            avg_confidence = df['confidence_score'].mean() * 100
            ttk.Label(metrics_frame, text=f"Average Confidence: {avg_confidence:.1f}%").pack(anchor=tk.W, pady=2)
        
        # Processing time metrics (if available)
        if 'processed_date' in df.columns:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_dtype(df['processed_date']):
                df['processed_date'] = pd.to_datetime(df['processed_date'], errors='coerce')
            
            # Get processing volume by day
            df['date'] = df['processed_date'].dt.date
            daily_counts = df.groupby('date').size()
            
            if not daily_counts.empty:
                avg_per_day = daily_counts.mean()
                max_per_day = daily_counts.max()
                
                ttk.Label(metrics_frame, text=f"Average Invoices/Day: {avg_per_day:.1f}").pack(anchor=tk.W, pady=2)
                ttk.Label(metrics_frame, text=f"Max Invoices/Day: {max_per_day}").pack(anchor=tk.W, pady=2)
    
    def _generate_confidence_analysis(self, df):
        """
        Generate confidence analysis visualization
        
        Args:
            df (pandas.DataFrame): Invoice dataframe
        """
        app_logger.debug("Generating confidence analysis")
        
        # Clear previous content
        for widget in self.confidence_frame.winfo_children():
            widget.destroy()
        
        if 'confidence_score' not in df.columns or df.empty:
            ttk.Label(self.confidence_frame, text="Confidence data not available").pack(pady=20)
            return
        
        # Create a figure for matplotlib
        fig = plt.Figure(figsize=(10, 6), dpi=100)
        
        # Create subplots
        gs = fig.add_gridspec(2, 2)
        ax1 = fig.add_subplot(gs[0, 0])  # Histogram
        ax2 = fig.add_subplot(gs[0, 1])  # Confidence by vendor
        ax3 = fig.add_subplot(gs[1, :])  # Confidence over time
        
        # 1. Confidence score distribution histogram
        confidence_values = df['confidence_score'] * 100  # Convert to percentage
        
        ax1.hist(confidence_values, bins=10, color='skyblue', edgecolor='black')
        ax1.set_title('Confidence Score Distribution')
        ax1.set_xlabel('Confidence Score (%)')
        ax1.set_ylabel('Number of Invoices')
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 2. Average confidence by vendor (top vendors)
        if 'vendor' in df.columns:
            # Group by vendor and calculate mean confidence
            vendor_confidence = df.groupby('vendor')['confidence_score'].mean() * 100
            
            # Sort and get top vendors
            vendor_confidence = vendor_confidence.sort_values(ascending=False)
            
            if len(vendor_confidence) > 5:
                vendor_confidence = vendor_confidence.head(5)
            
            vendor_confidence.plot(kind='bar', ax=ax2, color='lightgreen')
            ax2.set_title('Avg Confidence by Top Vendors')
            ax2.set_xlabel('Vendor')
            ax2.set_ylabel('Avg Confidence (%)')
            ax2.set_ylim([0, 100])
            
            # Rotate x-axis labels for better readability
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        else:
            ax2.set_title('Vendor data not available')
        
        # 3. Confidence over time
        if 'processed_date' in df.columns:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_dtype(df['processed_date']):
                df['processed_date'] = pd.to_datetime(df['processed_date'], errors='coerce')
            
            # Sort by date
            df_sorted = df.sort_values('processed_date')
            
            # Create 7-day rolling average of confidence
            df_sorted['date'] = df_sorted['processed_date'].dt.date
            df_grouped = df_sorted.groupby('date')['confidence_score'].mean() * 100
            
            if not df_grouped.empty and len(df_grouped) > 1:
                # Plot time series
                df_grouped.plot(ax=ax3, marker='o', linestyle='-', color='orange')
                
                # Add rolling average if enough data points
                if len(df_grouped) > 3:
                    rolling_avg = df_grouped.rolling(window=3, min_periods=1).mean()
                    rolling_avg.plot(ax=ax3, linestyle='--', color='red', label='3-day Rolling Avg')
                
                ax3.set_title('Confidence Score Over Time')
                ax3.set_xlabel('Date')
                ax3.set_ylabel('Avg Confidence Score (%)')
                ax3.legend()
                ax3.grid(True, linestyle='--', alpha=0.7)
            else:
                ax3.set_title('Not enough time data for trend analysis')
        else:
            ax3.set_title('Date data not available')
        
        # Adjust layout
        fig.tight_layout()
        
        # Embed in canvas
        canvas = FigureCanvasTkAgg(fig, self.confidence_frame)
        self.confidence_canvas = canvas
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def export_charts(self):
        """Export charts to image files"""
        app_logger.info("Exporting analytics charts")
        
        if not (self.vendor_canvas or self.time_canvas or self.performance_canvas or self.confidence_canvas):
            app_logger.warning("No charts to export")
            messagebox.showwarning("No Charts", "Please generate analytics first.")
            return
        
        try:
            # Create exports directory
            from invoice_processor.config import DATA_DIR
            export_dir = os.path.join(DATA_DIR, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # List to track exported files
            exported_files = []
            
            # Export vendor chart
            if self.vendor_canvas:
                filename = os.path.join(export_dir, f"vendor_analysis_{timestamp}.png")
                self.vendor_canvas.figure.savefig(filename, dpi=300, bbox_inches='tight')
                exported_files.append(filename)
                app_logger.debug(f"Vendor chart exported to {filename}")
            
            # Export time chart
            if self.time_canvas:
                filename = os.path.join(export_dir, f"time_analysis_{timestamp}.png")
                self.time_canvas.figure.savefig(filename, dpi=300, bbox_inches='tight')
                exported_files.append(filename)
                app_logger.debug(f"Time chart exported to {filename}")
            
            # Export performance chart
            if self.performance_canvas:
                filename = os.path.join(export_dir, f"performance_metrics_{timestamp}.png")
                self.performance_canvas.figure.savefig(filename, dpi=300, bbox_inches='tight')
                exported_files.append(filename)
                app_logger.debug(f"Performance chart exported to {filename}")
            
            # Export confidence chart
            if self.confidence_canvas:
                filename = os.path.join(export_dir, f"confidence_analysis_{timestamp}.png")
                self.confidence_canvas.figure.savefig(filename, dpi=300, bbox_inches='tight')
                exported_files.append(filename)
                app_logger.debug(f"Confidence chart exported to {filename}")
            
            if exported_files:
                self.status_var.set(f"Exported {len(exported_files)} charts to {export_dir}")
                app_logger.info(f"Exported {len(exported_files)} charts")
                messagebox.showinfo("Export Successful", f"Exported {len(exported_files)} charts to:\n{export_dir}")
            else:
                app_logger.warning("No charts were exported")
                self.status_var.set("No charts were exported")
                messagebox.showwarning("Export Failed", "No charts were exported.")
                
        except Exception as e:
            app_logger.error(f"Error exporting charts: {str(e)}")
            self.status_var.set(f"Error exporting charts: {str(e)}")
            messagebox.showerror("Export Error", f"An error occurred exporting charts:\n\n{str(e)}")