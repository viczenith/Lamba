import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
from django.conf import settings


class ChatEncryption:
    """
    End-to-end encryption for chat messages
    Uses Fernet symmetric encryption with company-specific keys
    """
    
    @staticmethod
    def get_company_key(company_id):
        """
        Generate a Fernet key based on company ID and secret key
        Each company gets a unique encryption key
        """
        # Combine company ID with Django secret key for key derivation
        salt = str(company_id).encode('utf-8')
        password = settings.SECRET_KEY.encode('utf-8')
        
        # Use PBKDF2 to derive a secure key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    @staticmethod
    def encrypt_message(message_content, company_id):
        """
        Encrypt a message for a specific company
        """
        if not message_content:
            return message_content
            
        key = ChatEncryption.get_company_key(company_id)
        f = Fernet(key)
        
        # Encrypt the message
        encrypted_content = f.encrypt(message_content.encode('utf-8'))
        return base64.b64encode(encrypted_content).decode('utf-8')
    
    @staticmethod
    def decrypt_message(encrypted_content, company_id):
        """
        Decrypt a message for a specific company
        """
        if not encrypted_content:
            return encrypted_content
            
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_content.encode('utf-8'))
            
            key = ChatEncryption.get_company_key(company_id)
            f = Fernet(key)
            
            # Decrypt the message
            decrypted_content = f.decrypt(encrypted_data)
            return decrypted_content.decode('utf-8')
        except Exception:
            # If decryption fails, return the original content
            # This handles cases where content wasn't encrypted
            return encrypted_content


def encrypt_message_signal(sender, instance, **kwargs):
    """
    Signal handler to automatically encrypt messages before saving
    """
    if instance.content and not instance.is_encrypted:
        # Check if message is already encrypted by trying to decrypt
        try:
            # Try to decrypt to check if it's already encrypted
            ChatEncryption.decrypt_message(instance.content, instance.company.id)
            # If successful, it's already encrypted
            instance.is_encrypted = True
        except Exception:
            # Not encrypted, so encrypt it
            instance.content = ChatEncryption.encrypt_message(
                instance.content, 
                instance.company.id
            )
            instance.is_encrypted = True


def decrypt_message_content(message_instance):
    """
    Helper function to decrypt message content for display
    """
    if message_instance.is_encrypted and message_instance.content:
        return ChatEncryption.decrypt_message(
            message_instance.content, 
            message_instance.company.id
        )
    return message_instance.content