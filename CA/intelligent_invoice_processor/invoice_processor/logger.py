import logging
import os
import datetime
from pathlib import Path

def setup_logger(name=None, log_level=logging.INFO):
    """
    Configure and return a logger instance
    
    Args:
        name (str, optional): Logger name. If None, returns the root logger
        log_level (int, optional): Logging level. Default is INFO
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate log filename with date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"invoice_processor_{today}.log"
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Check if handlers are already configured
    if not logger.handlers:
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Get the main application logger
app_logger = setup_logger('invoice_processor')