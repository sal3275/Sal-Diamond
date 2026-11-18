import cv2
import pytesseract
import re

def scan_receipt(image_path):
    # Load image using OpenCV
    img = cv2.imread(image_path)
    
    # Optional: Preprocess image (convert to grayscale and threshold for better OCR accuracy)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Run OCR on the image
    text = pytesseract.image_to_string(gray)
    
    # Use regular expressions to extract specific fields
    data = {}
    
    # Extract Purchase #
    purchase_match = re.search(r"Purchase\s*#:\s*(\d+)", text)
    if purchase_match:
        data["purchase_number"] = purchase_match.group(1)
        
    # Extract Reference #
    ref_match = re.search(r"Reference\s*#:\s*([A-Za-z0-9]+)", text)
    if ref_match:
        data["reference_number"] = ref_match.group(1)
        
    # Extract Original Amount
    amount_match = re.search(r"Original amount:\s*([\d\.]+)\s*([A-Z]+)", text)
    if amount_match:
        data["amount"] = amount_match.group(1)
        data["currency"] = amount_match.group(2)
        
    # Extract Transaction Code (Khmer text label context or numbers)
    code_match = re.search(r"(\d{10,})", text)
    if code_match:
        data["transaction_code"] = code_match.group(1)

    return data

# Example usage in your bot:
# extracted_data = scan_receipt("path_to_screenshot.png")
# print(extracted_data)