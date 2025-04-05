"""
Image processing utilities for invoice processing.

This module provides helper functions for image processing.
"""

import cv2
import numpy as np
from PIL import Image

from invoice_processor.logger import app_logger

def enhance_image_for_ocr(image):
    """
    Apply image enhancement techniques to improve OCR accuracy
    
    Args:
        image (PIL.Image): Input image
        
    Returns:
        PIL.Image: Enhanced image
    """
    app_logger.debug("Enhancing image for OCR")
    
    try:
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Check if image is already grayscale
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Deskew if needed
        # This would require calculating skew angle, which we'll skip for now
        
        # Convert back to PIL Image
        return Image.fromarray(opening)
    
    except Exception as e:
        app_logger.error(f"Error enhancing image: {str(e)}")
        # Return original image if enhancement fails
        return image

def deskew_image(image):
    """
    Correct the skew (rotation) of an image
    
    Args:
        image (PIL.Image): Input image
        
    Returns:
        PIL.Image: Deskewed image
    """
    app_logger.debug("Deskewing image")
    
    try:
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Threshold the image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Find all contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the rotated rectangles
        angles = []
        for contour in contours:
            # Filter small contours
            if cv2.contourArea(contour) < 100:
                continue
                
            # Get rotated rectangle
            rect = cv2.minAreaRect(contour)
            angle = rect[2]
            
            # Adjust angle
            if angle < -45:
                angle = 90 + angle
            
            angles.append(angle)
        
        # If we found angles, use the most common angle
        if angles:
            # Use the median angle to avoid outliers
            from statistics import median
            skew_angle = median(angles)
        else:
            # No significant skew detected
            skew_angle = 0
        
        # If the skew is minimal, return the original image
        if abs(skew_angle) < 0.5:
            return image
        
        # Rotate the image to correct the skew
        height, width = gray.shape
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        rotated = cv2.warpAffine(img_array, rotation_matrix, (width, height), 
                                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # Convert back to PIL Image
        return Image.fromarray(rotated)
    
    except Exception as e:
        app_logger.error(f"Error deskewing image: {str(e)}")
        # Return original image if deskewing fails
        return image

def remove_noise(image):
    """
    Remove noise from an image using various techniques
    
    Args:
        image (PIL.Image): Input image
        
    Returns:
        PIL.Image: Noise-reduced image
    """
    app_logger.debug("Removing noise from image")
    
    try:
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Apply bilateral filter to remove noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Remove small noise with morphological operations
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, kernel)
        
        # Convert back to PIL Image
        return Image.fromarray(opening)
    
    except Exception as e:
        app_logger.error(f"Error removing noise: {str(e)}")
        # Return original image if noise removal fails
        return image

def adjust_contrast(image, clip_limit=2.0, tile_grid_size=(8, 8)):
    """
    Adjust contrast of an image using adaptive histogram equalization
    
    Args:
        image (PIL.Image): Input image
        clip_limit (float): Threshold for contrast limiting
        tile_grid_size (tuple): Size of grid for histogram equalization
        
    Returns:
        PIL.Image: Contrast-enhanced image
    """
    app_logger.debug("Adjusting image contrast")
    
    try:
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Create CLAHE object (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        enhanced = clahe.apply(gray)
        
        # Convert back to PIL Image
        return Image.fromarray(enhanced)
    
    except Exception as e:
        app_logger.error(f"Error adjusting contrast: {str(e)}")
        # Return original image if contrast adjustment fails
        return image

def resize_image(image, dpi=300):
    """
    Resize image to specified DPI while maintaining aspect ratio
    
    Args:
        image (PIL.Image): Input image
        dpi (int): Target DPI
        
    Returns:
        PIL.Image: Resized image
    """
    app_logger.debug(f"Resizing image to {dpi} DPI")
    
    try:
        # Get current DPI if available
        current_dpi = image.info.get('dpi', (72, 72))
        if isinstance(current_dpi, tuple):
            current_dpi = current_dpi[0]
        
        # Calculate scale factor
        scale = dpi / current_dpi
        
        # If scale is close to 1, no need to resize
        if 0.95 <= scale <= 1.05:
            return image
        
        # Calculate new dimensions
        width, height = image.size
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize image
        resized = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Set DPI in the image info
        resized.info['dpi'] = (dpi, dpi)
        
        return resized
    
    except Exception as e:
        app_logger.error(f"Error resizing image: {str(e)}")
        # Return original image if resizing fails
        return image