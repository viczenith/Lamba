"""
Dynamic URL Manager for SuperAdmin
Generates and manages secure, obfuscated URLs for admin access
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import os


class DynamicURLManager:
    """
    Manages dynamic URL slugs for super admin access
    URLs change periodically for enhanced security
    """
    
    CACHE_KEY_CURRENT = 'superadmin_current_url_slug'
    CACHE_KEY_VALID_SLUGS = 'superadmin_valid_url_slugs'
    CACHE_KEY_SLUG_CREATED = 'superadmin_slug_created_at'
    
    # URL rotation period (in seconds)
    ROTATION_PERIOD = 86400  # 24 hours
    
    # Keep old URLs valid for grace period
    GRACE_PERIOD = 3600  # 1 hour
    
    @classmethod
    def get_current_slug(cls):
        """
        Get the current valid admin URL slug
        Generates a new one if needed
        """
        current_slug = cache.get(cls.CACHE_KEY_CURRENT)
        
        if not current_slug or cls._should_rotate():
            current_slug = cls._generate_new_slug()
        
        return current_slug
    
    @classmethod
    def get_admin_url(cls, path=''):
        """
        Get the full admin URL with current slug
        """
        slug = cls.get_current_slug()
        base = f'/super-admin-{slug}/'
        return base + path.lstrip('/')
    
    @classmethod
    def is_valid_slug(cls, slug):
        """
        Check if a slug is currently valid
        """
        if not slug:
            return False
        
        # Check if it's the current slug
        current_slug = cache.get(cls.CACHE_KEY_CURRENT)
        if slug == current_slug:
            return True
        
        # Check if it's in the grace period
        valid_slugs = cache.get(cls.CACHE_KEY_VALID_SLUGS, [])
        return slug in valid_slugs
    
    @classmethod
    def _generate_new_slug(cls):
        """
        Generate a new secure URL slug
        """
        # Generate cryptographically secure random slug
        random_bytes = secrets.token_bytes(32)
        timestamp = str(datetime.now().timestamp()).encode()
        
        # Combine random data with timestamp
        combined = random_bytes + timestamp
        
        # Create hash
        slug = hashlib.sha256(combined).hexdigest()[:32]
        
        # Get old slugs for grace period
        old_current = cache.get(cls.CACHE_KEY_CURRENT)
        valid_slugs = []
        
        if old_current:
            valid_slugs.append(old_current)
        
        # Store new slug
        cache.set(cls.CACHE_KEY_CURRENT, slug, cls.ROTATION_PERIOD + cls.GRACE_PERIOD)
        cache.set(cls.CACHE_KEY_VALID_SLUGS, valid_slugs, cls.GRACE_PERIOD)
        cache.set(cls.CACHE_KEY_SLUG_CREATED, datetime.now().isoformat(), cls.ROTATION_PERIOD)
        
        # Save to environment file for server restarts
        cls._save_to_env(slug)
        
        return slug
    
    @classmethod
    def _should_rotate(cls):
        """
        Check if URL should be rotated
        """
        created_at_str = cache.get(cls.CACHE_KEY_SLUG_CREATED)
        
        if not created_at_str:
            return True
        
        try:
            created_at = datetime.fromisoformat(created_at_str)
            age = (datetime.now() - created_at).total_seconds()
            return age >= cls.ROTATION_PERIOD
        except Exception:
            return True
    
    @classmethod
    def _save_to_env(cls, slug):
        """
        Save current slug to .env file for persistence across restarts
        """
        try:
            env_file = os.path.join(settings.BASE_DIR, '.env.superadmin')
            with open(env_file, 'w') as f:
                f.write(f"SUPERADMIN_URL_SLUG={slug}\n")
                f.write(f"CREATED_AT={datetime.now().isoformat()}\n")
        except Exception:
            pass  # Fail silently if can't write
    
    @classmethod
    def load_from_env(cls):
        """
        Load slug from .env file on server startup
        """
        try:
            env_file = os.path.join(settings.BASE_DIR, '.env.superadmin')
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                    slug = None
                    created_at = None
                    
                    for line in lines:
                        if line.startswith('SUPERADMIN_URL_SLUG='):
                            slug = line.split('=')[1].strip()
                        elif line.startswith('CREATED_AT='):
                            created_at = line.split('=')[1].strip()
                    
                    if slug and created_at:
                        # Check if still valid
                        created = datetime.fromisoformat(created_at)
                        age = (datetime.now() - created).total_seconds()
                        
                        if age < cls.ROTATION_PERIOD:
                            # Still valid, restore to cache
                            remaining = cls.ROTATION_PERIOD - age
                            cache.set(cls.CACHE_KEY_CURRENT, slug, int(remaining) + cls.GRACE_PERIOD)
                            cache.set(cls.CACHE_KEY_SLUG_CREATED, created_at, int(remaining))
                            return slug
        except Exception:
            pass
        
        # Generate new if can't load or expired
        return cls._generate_new_slug()


# Initialize on import
DynamicURLManager.load_from_env()
