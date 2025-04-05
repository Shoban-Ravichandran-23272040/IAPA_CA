"""
Machine learning module for vendor classification.

This module provides a classifier that can identify invoice vendors
based on text content using machine learning techniques.
"""

import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from fuzzywuzzy import process

from invoice_processor.config import MODEL_PATH, ML_TRAIN_SAMPLES_PER_VENDOR
from invoice_processor.logger import app_logger
from invoice_processor.data.vendor_database import VENDOR_DATABASE

class VendorClassifier:
    """
    Machine learning classifier for identifying vendors from invoice text
    """
    
    def __init__(self):
        """Initialize the classifier with vectorizer and model"""
        app_logger.debug("Initializing VendorClassifier")
        self.vectorizer = CountVectorizer(analyzer='word', ngram_range=(1, 2))
        self.model = RandomForestClassifier(n_estimators=100)
        self.classes = list(VENDOR_DATABASE.keys())
        
    def train(self, training_data):
        """
        Train the classifier with labeled examples
        
        Args:
            training_data (list): List of (text, vendor_name) tuples
        """
        app_logger.info(f"Training vendor classifier with {len(training_data)} examples")
        
        # Training data should be list of (text, vendor_name) tuples
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        # Verify we have examples of each vendor
        unique_labels = set(labels)
        app_logger.debug(f"Training data contains {len(unique_labels)} unique vendors")
        
        # Vectorize the text
        X = self.vectorizer.fit_transform(texts)
        app_logger.debug(f"Vectorized text with {X.shape[1]} features")
        
        # Train the model
        self.model.fit(X, labels)
        app_logger.info("Vendor classifier training complete")
    
    def predict(self, text):
        """
        Predict vendor from invoice text
        
        Args:
            text (str): Invoice text to classify
            
        Returns:
            tuple: (predicted_vendor, confidence_score)
        """
        try:
            # Vectorize the input text
            X = self.vectorizer.transform([text])
            
            # Get prediction and probability
            prediction = self.model.predict(X)[0]
            proba = self.model.predict_proba(X)[0]
            max_proba = max(proba)
            
            app_logger.debug(f"Predicted vendor: {prediction} with confidence: {max_proba:.2f}")
            return prediction, max_proba
        except Exception as e:
            app_logger.error(f"Error in vendor prediction: {str(e)}")
            # Fall back to fuzzy matching if ML prediction fails
            app_logger.debug("Falling back to fuzzy matching")
            return self._fuzzy_match_vendor(text)
    
    def _fuzzy_match_vendor(self, text):
        """
        Fallback method using fuzzy matching when ML prediction fails
        
        Args:
            text (str): Invoice text to match
            
        Returns:
            tuple: (matched_vendor, confidence_score)
        """
        # Extract first few lines for matching
        first_lines = '\n'.join(text.split('\n')[:5])
        vendor_match = process.extractOne(first_lines, self.classes)
        vendor = vendor_match[0]
        confidence = vendor_match[1] / 100.0  # Convert to 0-1 scale
        
        app_logger.debug(f"Fuzzy matched vendor: {vendor} with confidence: {confidence:.2f}")
        return vendor, confidence
    
    def save_model(self, path=None):
        """
        Save the trained model to disk
        
        Args:
            path (str, optional): Path to save model. Defaults to MODEL_PATH from config.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if path is None:
            path = MODEL_PATH
            
        try:
            app_logger.info(f"Saving vendor classifier model to {path}")
            with open(path, 'wb') as f:
                pickle.dump((self.vectorizer, self.model, self.classes), f)
            return True
        except Exception as e:
            app_logger.error(f"Error saving model: {str(e)}")
            return False
    
    def load_model(self, path=None):
        """
        Load a trained model from disk
        
        Args:
            path (str, optional): Path to load model from. Defaults to MODEL_PATH from config.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if path is None:
            path = MODEL_PATH
            
        try:
            if os.path.exists(path):
                app_logger.info(f"Loading vendor classifier model from {path}")
                with open(path, 'rb') as f:
                    self.vectorizer, self.model, self.classes = pickle.load(f)
                app_logger.debug(f"Model loaded successfully with {len(self.classes)} vendor classes")
                return True
            else:
                app_logger.warning(f"Model file not found: {path}")
                return False
        except Exception as e:
            app_logger.error(f"Error loading model: {str(e)}")
            return False

def generate_training_data(num_samples_per_vendor=ML_TRAIN_SAMPLES_PER_VENDOR):
    """
    Generate synthetic training data for vendor classification
    
    Args:
        num_samples_per_vendor (int): Number of samples to generate per vendor
        
    Returns:
        list: List of (text, vendor_name) tuples for training
    """
    app_logger.info(f"Generating {num_samples_per_vendor} training samples per vendor")
    training_data = []
    
    import random
    
    # Generate training examples for each vendor
    for vendor_name, vendor_info in VENDOR_DATABASE.items():
        # Basic invoice template with vendor information
        template = f"""
        {vendor_name}
        {vendor_info['address']}
        Tax ID: {vendor_info['tax_id']}
        
        INVOICE
        
        Invoice No: INV-{vendor_name[:3].upper()}-12345
        Date: 03/15/2024
        Due Date: 04/15/2024
        PO Number: PO-2024-001
        
        Payment Terms: {vendor_info['payment_terms']}
        """
        
        # Add some variations of this template
        for i in range(num_samples_per_vendor):
            # Slightly modify the text each time
            variation = template.replace("INV-", f"INV{i}-")
            variation = variation.replace("03/15/2024", f"03/{15+i if 15+i <= 30 else 15}/2024")
            variation = variation.replace("PO-2024-001", f"PO-2024-{1000+i}")
            
            # Add some random items from this vendor's typical items
            items_section = "\nItems:\n"
            for _ in range(random.randint(1, 4)):
                item = random.choice(vendor_info['typical_items'])
                qty = random.randint(1, 10)
                price = round(random.uniform(10, 200), 2)
                total = qty * price
                items_section += f"{item} {qty} ${price:.2f} ${total:.2f}\n"
            
            variation += items_section
            
            # Add to training data
            training_data.append((variation, vendor_name))
    
    app_logger.debug(f"Generated {len(training_data)} total training examples")
    return training_data