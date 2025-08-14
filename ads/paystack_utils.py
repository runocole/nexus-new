import requests
import string
import random
from django.conf import settings

def generate_transaction_reference():
    """Generate a unique transaction reference"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

def initialize_transaction(email, amount, metadata=None):
    """
    Initialize a Paystack transaction
    
    Args:
        email (str): Customer's email
        amount (int): Amount in kobo (multiply naira by 100)
        metadata (dict, optional): Additional data
        
    Returns:
        dict: Response from Paystack API
    """
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": amount * 100,  # Convert to kobo
        "callback_url": settings.PAYSTACK_CALLBACK_URL,
        "reference": generate_transaction_reference()
    }
    
    if metadata:
        data["metadata"] = metadata
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def verify_transaction(reference):
    """
    Verify a Paystack transaction
    
    Args:
        reference (str): Transaction reference
        
    Returns:
        dict: Response from Paystack API
    """
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    
    response = requests.get(url, headers=headers)
    return response.json()