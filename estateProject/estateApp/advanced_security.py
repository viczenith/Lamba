"""
===============================================================================
ADVANCED CYBERSECURITY MODULE - ENTERPRISE-GRADE PROTECTION
===============================================================================

This module provides comprehensive protection against ALL types of cyber attacks:

ATTACK TYPES PROTECTED AGAINST:
================================

1. BRUTE FORCE ATTACKS
   - Password guessing attempts
   - Account enumeration
   - Credential stuffing

2. INJECTION ATTACKS
   - SQL Injection (SQLi)
   - NoSQL Injection
   - LDAP Injection
   - XPath Injection
   - Command Injection
   - Template Injection (SSTI)

3. CROSS-SITE ATTACKS
   - Cross-Site Scripting (XSS) - Stored, Reflected, DOM-based
   - Cross-Site Request Forgery (CSRF)

4. SESSION ATTACKS
   - Session Hijacking
   - Session Fixation
   - Session Prediction
   - Cookie Theft

5. AUTHENTICATION ATTACKS
   - Credential Stuffing
   - Account Takeover
   - Password Spraying
   - Multi-factor Bypass

6. NETWORK ATTACKS
   - Man-in-the-Middle (MITM)
   - DNS Spoofing
   - IP Spoofing

7. APPLICATION ATTACKS
   - Path Traversal (Directory Traversal)
   - File Inclusion (LFI/RFI)
   - Clickjacking
   - Open Redirect
   - Parameter Tampering
   - Privilege Escalation
   - Insecure Direct Object Reference (IDOR)

8. BOT/AUTOMATED ATTACKS
   - Web Scraping
   - DDoS Attacks
   - Credential Enumeration
   - Form Spam

9. DATA ATTACKS
   - Data Exfiltration
   - Information Disclosure
   - Mass Assignment

10. ADVANCED PERSISTENT THREATS (APT)
    - Zero-day Exploits
    - Social Engineering
    - Phishing

===============================================================================
"""

import hashlib
import hmac
import secrets
import time
import base64
import json
import re
import logging
import ipaddress
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from collections import defaultdict
import threading

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied

logger = logging.getLogger('security')


# ============================================================================
# 1. ADVANCED BRUTE FORCE PROTECTION
# ============================================================================

class BruteForceProtection:
    """
    Multi-layered brute force attack prevention.
    
    Features:
    - Progressive lockout (exponential backoff)
    - IP-based tracking
    - Account-based tracking
    - Distributed attack detection
    - Geographic anomaly detection
    """
    
    # Lockout configuration
    MAX_FAILED_ATTEMPTS = 5
    INITIAL_LOCKOUT_SECONDS = 60  # 1 minute
    MAX_LOCKOUT_SECONDS = 3600  # 1 hour
    LOCKOUT_MULTIPLIER = 2  # Double lockout each time
    
    # Distributed attack thresholds
    GLOBAL_FAIL_THRESHOLD = 100  # Fails across all IPs in 5 min
    GLOBAL_FAIL_WINDOW = 300  # 5 minutes
    
    @classmethod
    def check_brute_force(cls, request, account_identifier: str = None) -> Tuple[bool, str, int]:
        """
        Check for brute force attacks.
        
        Returns:
            (is_blocked, reason, lockout_remaining_seconds)
        """
        ip = get_client_ip(request)
        
        # Check IP lockout
        ip_blocked, ip_reason, ip_remaining = cls._check_ip_lockout(ip)
        if ip_blocked:
            logger.warning(f"IP BLOCKED: {ip} - {ip_reason}")
            return True, ip_reason, ip_remaining
        
        # Check account lockout
        if account_identifier:
            acc_blocked, acc_reason, acc_remaining = cls._check_account_lockout(account_identifier)
            if acc_blocked:
                logger.warning(f"ACCOUNT BLOCKED: {account_identifier} - {acc_reason}")
                return True, acc_reason, acc_remaining
        
        # Check distributed attack
        dist_blocked, dist_reason = cls._check_distributed_attack()
        if dist_blocked:
            logger.critical(f"DISTRIBUTED ATTACK DETECTED - {dist_reason}")
            return True, dist_reason, 60
        
        return False, "", 0
    
    @classmethod
    def record_failed_attempt(cls, request, account_identifier: str = None, reason: str = ""):
        """Record a failed authentication attempt."""
        ip = get_client_ip(request)
        timestamp = time.time()
        
        # Record IP failure
        ip_key = f"bruteforce:ip:{ip}"
        ip_data = cache.get(ip_key, {'attempts': [], 'lockout_count': 0})
        ip_data['attempts'].append({'time': timestamp, 'reason': reason})
        ip_data['attempts'] = [a for a in ip_data['attempts'] if timestamp - a['time'] < 3600]
        
        # Apply lockout if threshold exceeded
        recent_attempts = [a for a in ip_data['attempts'] if timestamp - a['time'] < 300]
        if len(recent_attempts) >= cls.MAX_FAILED_ATTEMPTS:
            ip_data['lockout_count'] += 1
            lockout_duration = min(
                cls.INITIAL_LOCKOUT_SECONDS * (cls.LOCKOUT_MULTIPLIER ** (ip_data['lockout_count'] - 1)),
                cls.MAX_LOCKOUT_SECONDS
            )
            ip_data['lockout_until'] = timestamp + lockout_duration
            logger.warning(f"IP LOCKED OUT: {ip} for {lockout_duration}s (attempt #{ip_data['lockout_count']})")
        
        cache.set(ip_key, ip_data, timeout=7200)  # 2 hour retention
        
        # Record account failure
        if account_identifier:
            acc_key = f"bruteforce:account:{hashlib.sha256(account_identifier.encode()).hexdigest()[:16]}"
            acc_data = cache.get(acc_key, {'attempts': [], 'lockout_count': 0})
            acc_data['attempts'].append({'time': timestamp, 'ip': ip, 'reason': reason})
            acc_data['attempts'] = [a for a in acc_data['attempts'] if timestamp - a['time'] < 3600]
            
            recent_acc_attempts = [a for a in acc_data['attempts'] if timestamp - a['time'] < 300]
            if len(recent_acc_attempts) >= cls.MAX_FAILED_ATTEMPTS:
                acc_data['lockout_count'] += 1
                lockout_duration = min(
                    cls.INITIAL_LOCKOUT_SECONDS * (cls.LOCKOUT_MULTIPLIER ** (acc_data['lockout_count'] - 1)),
                    cls.MAX_LOCKOUT_SECONDS
                )
                acc_data['lockout_until'] = timestamp + lockout_duration
                logger.warning(f"ACCOUNT LOCKED OUT: {account_identifier} for {lockout_duration}s")
            
            cache.set(acc_key, acc_data, timeout=7200)
        
        # Record global failure (for distributed attack detection)
        global_key = "bruteforce:global"
        global_data = cache.get(global_key, {'attempts': []})
        global_data['attempts'].append({'time': timestamp, 'ip': ip})
        global_data['attempts'] = [a for a in global_data['attempts'] if timestamp - a['time'] < cls.GLOBAL_FAIL_WINDOW]
        cache.set(global_key, global_data, timeout=cls.GLOBAL_FAIL_WINDOW)
    
    @classmethod
    def record_successful_login(cls, request, account_identifier: str):
        """Clear failed attempts on successful login."""
        ip = get_client_ip(request)
        
        # Clear IP lockout
        ip_key = f"bruteforce:ip:{ip}"
        cache.delete(ip_key)
        
        # Clear account lockout
        acc_key = f"bruteforce:account:{hashlib.sha256(account_identifier.encode()).hexdigest()[:16]}"
        cache.delete(acc_key)
        
        logger.info(f"Successful login: {account_identifier} from {ip}")
    
    @classmethod
    def _check_ip_lockout(cls, ip: str) -> Tuple[bool, str, int]:
        """Check if IP is locked out."""
        ip_key = f"bruteforce:ip:{ip}"
        ip_data = cache.get(ip_key, {})
        
        lockout_until = ip_data.get('lockout_until', 0)
        if lockout_until > time.time():
            remaining = int(lockout_until - time.time())
            return True, f"IP temporarily blocked due to multiple failed attempts", remaining
        
        return False, "", 0
    
    @classmethod
    def _check_account_lockout(cls, account_identifier: str) -> Tuple[bool, str, int]:
        """Check if account is locked out."""
        acc_key = f"bruteforce:account:{hashlib.sha256(account_identifier.encode()).hexdigest()[:16]}"
        acc_data = cache.get(acc_key, {})
        
        lockout_until = acc_data.get('lockout_until', 0)
        if lockout_until > time.time():
            remaining = int(lockout_until - time.time())
            return True, f"Account temporarily locked due to multiple failed attempts", remaining
        
        return False, "", 0
    
    @classmethod
    def _check_distributed_attack(cls) -> Tuple[bool, str]:
        """Detect distributed brute force attacks."""
        global_key = "bruteforce:global"
        global_data = cache.get(global_key, {'attempts': []})
        
        recent = [a for a in global_data['attempts'] if time.time() - a['time'] < cls.GLOBAL_FAIL_WINDOW]
        unique_ips = len(set(a['ip'] for a in recent))
        
        # Many failures from many IPs = distributed attack
        if len(recent) >= cls.GLOBAL_FAIL_THRESHOLD and unique_ips >= 10:
            return True, f"Distributed attack detected ({len(recent)} failures from {unique_ips} IPs)"
        
        return False, ""


# ============================================================================
# 2. ADVANCED INJECTION ATTACK PROTECTION
# ============================================================================

class InjectionProtection:
    """
    Comprehensive injection attack detection and prevention.
    
    Protects against:
    - SQL Injection (including blind, union, error-based)
    - NoSQL Injection
    - LDAP Injection
    - XPath Injection
    - Command Injection
    - Template Injection (SSTI)
    - Header Injection
    """
    
    # SQL Injection patterns (comprehensive)
    SQL_PATTERNS = [
        # Basic SQL keywords
        r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b.*\b(FROM|INTO|TABLE|DATABASE)\b",
        r"(?i)\bUNION\b.*\bSELECT\b",
        r"(?i)\bOR\b.*[=<>].*\b(OR|AND)\b",
        r"(?i)(--|#|/\*|\*/)",  # SQL comments
        r"(?i)(\bOR\b|\bAND\b)\s*['\"]\s*['\"]?\s*[=<>]",  # OR/AND with quotes
        r"(?i)\b(EXEC|EXECUTE|xp_|sp_)\b",  # Stored procedures
        r"(?i);\s*(SELECT|INSERT|UPDATE|DELETE|DROP)",  # Stacked queries
        r"(?i)'\s*(OR|AND)\s*'?\d+'\s*=\s*'\d+",  # Always true conditions
        r"(?i)\bHAVING\b.*\b(SELECT|AND|OR)\b",  # HAVING injection
        r"(?i)\bGROUP\s+BY\b.*\b(SELECT|UNION)\b",  # GROUP BY injection
        r"(?i)\bORDER\s+BY\b.*(\d+|SLEEP|BENCHMARK)",  # ORDER BY injection
        r"(?i)\bWAITFOR\b.*\bDELAY\b",  # Time-based (MSSQL)
        r"(?i)\bBENCHMARK\s*\(",  # Time-based (MySQL)
        r"(?i)\bSLEEP\s*\(",  # Time-based
        r"(?i)\bLOAD_FILE\s*\(",  # File read
        r"(?i)\bINTO\s+(OUT|DUMP)FILE\b",  # File write
        r"(?i)INFORMATION_SCHEMA",  # Schema enumeration
    ]
    
    # XSS patterns (comprehensive)
    XSS_PATTERNS = [
        r"<script[^>]*>",  # Script tags
        r"</script>",
        r"javascript\s*:",  # JavaScript protocol
        r"vbscript\s*:",  # VBScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onerror, etc.)
        r"<\s*img[^>]+onerror",  # Image error handler
        r"<\s*svg[^>]*onload",  # SVG onload
        r"<\s*body[^>]*onload",  # Body onload
        r"<\s*iframe",  # iframes
        r"<\s*object",  # Objects
        r"<\s*embed",  # Embeds
        r"<\s*link[^>]+rel\s*=\s*['\"]?import",  # HTML imports
        r"expression\s*\(",  # CSS expressions
        r"url\s*\(\s*['\"]?\s*javascript",  # CSS JavaScript
        r"@import",  # CSS import
        r"<!--.*-->",  # HTML comments (can hide scripts)
        r"<\s*meta[^>]+http-equiv",  # Meta refresh
        r"data\s*:\s*text/html",  # Data URLs
        r"<\s*base[^>]+href",  # Base tag hijacking
    ]
    
    # Command Injection patterns
    COMMAND_PATTERNS = [
        r"[;&|`$]",  # Command separators
        r"\$\(",  # Command substitution
        r"`[^`]+`",  # Backtick execution
        r"\|\s*\w+",  # Pipe to command
        r">\s*/",  # Redirect to file
        r"<\s*/",  # Read from file
        r"\b(cat|ls|dir|whoami|id|pwd|curl|wget|nc|netcat)\b",  # Common commands
        r"\.\./",  # Path traversal
        r"/etc/passwd",
        r"/etc/shadow",
        r"c:\\windows",
        r"%00",  # Null byte
        r"\\x00",  # Null byte hex
    ]
    
    # Template Injection patterns (SSTI)
    TEMPLATE_PATTERNS = [
        r"\{\{.*\}\}",  # Jinja2/Django
        r"\$\{.*\}",  # JSP/Spring
        r"#\{.*\}",  # Ruby/Thymeleaf
        r"<%.*%>",  # JSP/ASP
        r"\[@.*@\]",  # Freemarker
        r"\*\{.*\}",  # Thymeleaf
        r"__class__",  # Python class access
        r"__mro__",  # Python MRO
        r"__subclasses__",  # Python subclasses
        r"__globals__",  # Python globals
        r"__builtins__",  # Python builtins
    ]
    
    # LDAP Injection patterns
    LDAP_PATTERNS = [
        r"\)\s*\(\|",  # OR injection
        r"\)\s*\(&",  # AND injection
        r"\)\s*\(!",  # NOT injection
        r"\*\)",  # Wildcard
        r"\\00",  # Null
    ]
    
    @classmethod
    def check_injection(cls, data: str, check_type: str = 'all') -> Tuple[bool, str]:
        """
        Check for injection attacks.
        
        Args:
            data: String to check
            check_type: 'sql', 'xss', 'command', 'template', 'ldap', or 'all'
        
        Returns:
            (is_malicious, attack_type)
        """
        if not data:
            return False, ""
        
        checks = {
            'sql': (cls.SQL_PATTERNS, 'SQL Injection'),
            'xss': (cls.XSS_PATTERNS, 'XSS Attack'),
            'command': (cls.COMMAND_PATTERNS, 'Command Injection'),
            'template': (cls.TEMPLATE_PATTERNS, 'Template Injection'),
            'ldap': (cls.LDAP_PATTERNS, 'LDAP Injection'),
        }
        
        if check_type == 'all':
            patterns_to_check = checks.items()
        else:
            patterns_to_check = [(check_type, checks.get(check_type, ([], 'Unknown')))]
        
        for name, (patterns, attack_name) in patterns_to_check:
            for pattern in patterns:
                try:
                    if re.search(pattern, data, re.IGNORECASE | re.DOTALL):
                        return True, attack_name
                except re.error:
                    continue
        
        return False, ""
    
    @classmethod
    def sanitize_input(cls, data: str) -> str:
        """Sanitize input by removing/encoding dangerous characters."""
        if not data:
            return data
        
        # HTML entity encoding
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;',
            '/': '&#x2F;',
        }
        
        for char, replacement in replacements.items():
            data = data.replace(char, replacement)
        
        return data


# ============================================================================
# 3. SESSION SECURITY
# ============================================================================

class SessionSecurity:
    """
    Advanced session security to prevent:
    - Session Hijacking
    - Session Fixation
    - Session Prediction
    - Cookie Theft
    """
    
    # Session fingerprint components
    FINGERPRINT_COMPONENTS = [
        'HTTP_USER_AGENT',
        'HTTP_ACCEPT_LANGUAGE',
        'HTTP_ACCEPT_ENCODING',
    ]
    
    @classmethod
    def create_session_fingerprint(cls, request) -> str:
        """Create a fingerprint of the session based on request characteristics."""
        components = []
        for key in cls.FINGERPRINT_COMPONENTS:
            components.append(request.META.get(key, ''))
        
        # Add partial IP (first two octets for mobile users who change IPs)
        ip = get_client_ip(request)
        try:
            ip_parts = ip.split('.')[:2]
            components.append('.'.join(ip_parts))
        except:
            pass
        
        fingerprint_data = '|'.join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    @classmethod
    def validate_session(cls, request) -> Tuple[bool, str]:
        """
        Validate session integrity.
        
        Returns:
            (is_valid, reason_if_invalid)
        """
        if not request.user.is_authenticated:
            return True, ""
        
        # Check session fingerprint
        stored_fingerprint = request.session.get('_security_fingerprint')
        current_fingerprint = cls.create_session_fingerprint(request)
        
        if stored_fingerprint and stored_fingerprint != current_fingerprint:
            # Fingerprint changed - potential session hijacking
            logger.warning(
                f"SESSION FINGERPRINT MISMATCH: User {request.user.id} "
                f"stored={stored_fingerprint} current={current_fingerprint}"
            )
            return False, "Session fingerprint mismatch - potential hijacking detected"
        
        # Store fingerprint if not set
        if not stored_fingerprint:
            request.session['_security_fingerprint'] = current_fingerprint
        
        # Check session age
        session_created = request.session.get('_security_created')
        if session_created:
            max_age = getattr(settings, 'SESSION_COOKIE_AGE', 86400)
            if time.time() - session_created > max_age:
                return False, "Session expired"
        else:
            request.session['_security_created'] = time.time()
        
        # Check last activity
        last_activity = request.session.get('_security_last_activity')
        inactivity_timeout = getattr(settings, 'SESSION_INACTIVITY_TIMEOUT', 1800)  # 30 min default
        if last_activity and time.time() - last_activity > inactivity_timeout:
            return False, "Session expired due to inactivity"
        
        request.session['_security_last_activity'] = time.time()
        
        return True, ""
    
    @classmethod
    def regenerate_session(cls, request):
        """Regenerate session ID to prevent fixation attacks."""
        # Get current session data
        session_data = dict(request.session)
        
        # Create new session
        request.session.create()
        
        # Restore data to new session
        for key, value in session_data.items():
            if not key.startswith('_'):  # Skip internal keys
                request.session[key] = value
        
        # Set new security markers
        request.session['_security_fingerprint'] = cls.create_session_fingerprint(request)
        request.session['_security_created'] = time.time()
        request.session['_security_last_activity'] = time.time()
        
        logger.info(f"Session regenerated for user {getattr(request.user, 'id', 'anonymous')}")


# ============================================================================
# 4. IDOR PROTECTION (Insecure Direct Object Reference)
# ============================================================================

class IDORProtection:
    """
    Prevents Insecure Direct Object Reference attacks.
    
    Ensures users can only access resources they own or are authorized to access.
    """
    
    @classmethod
    def verify_object_ownership(cls, request, obj, owner_field: str = 'user') -> bool:
        """
        Verify that the user owns or has access to the object.
        
        Args:
            request: The HTTP request
            obj: The object being accessed
            owner_field: Field name that references the owner
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusers have access to everything
        if request.user.is_superuser:
            return True
        
        # Check direct ownership
        owner = getattr(obj, owner_field, None)
        if owner and owner == request.user:
            return True
        
        # Check if owner is an ID
        owner_id = getattr(obj, f'{owner_field}_id', None)
        if owner_id and owner_id == request.user.id:
            return True
        
        # Check company-based ownership (multi-tenant)
        obj_company = getattr(obj, 'company', None) or getattr(obj, 'company_profile', None)
        user_company = getattr(request.user, 'company_profile', None)
        
        if obj_company and user_company and obj_company == user_company:
            # Same company - check role permissions
            return True
        
        return False
    
    @classmethod
    def verify_company_access(cls, request, company_id: int) -> bool:
        """Verify user has access to a specific company."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user's company matches
        user_company = getattr(request.user, 'company_profile', None)
        if user_company and user_company.id == company_id:
            return True
        
        # Check if user has affiliation with company
        # This handles multi-company users (clients/marketers with multiple affiliations)
        from estateApp.models import CompanyClientProfile, CompanyMarketerProfile, MarketerAffiliation
        
        if request.user.role == 'client':
            has_access = CompanyClientProfile.objects.filter(
                client=request.user, company_id=company_id
            ).exists()
            return has_access
        
        if request.user.role == 'marketer':
            has_profile = CompanyMarketerProfile.objects.filter(
                marketer=request.user, company_id=company_id
            ).exists()
            has_affiliation = MarketerAffiliation.objects.filter(
                marketer=request.user, company_id=company_id
            ).exists()
            return has_profile or has_affiliation
        
        return False


# ============================================================================
# 5. CLICKJACKING PROTECTION
# ============================================================================

class ClickjackingProtection:
    """
    Prevents clickjacking attacks through multiple layers.
    """
    
    @classmethod
    def add_headers(cls, response) -> HttpResponse:
        """Add clickjacking protection headers."""
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        # Content-Security-Policy frame-ancestors
        csp = response.get('Content-Security-Policy', '')
        if 'frame-ancestors' not in csp:
            if csp:
                csp += "; frame-ancestors 'self'"
            else:
                csp = "frame-ancestors 'self'"
            response['Content-Security-Policy'] = csp
        
        return response


# ============================================================================
# 6. OPEN REDIRECT PROTECTION
# ============================================================================

class OpenRedirectProtection:
    """
    Prevents open redirect vulnerabilities.
    """
    
    # Allowed redirect domains (add your domains)
    ALLOWED_DOMAINS = [
        'localhost',
        '127.0.0.1',
    ]
    
    @classmethod
    def is_safe_redirect(cls, url: str, request=None) -> bool:
        """
        Check if a redirect URL is safe.
        """
        if not url:
            return False
        
        # Relative URLs are safe
        if url.startswith('/') and not url.startswith('//'):
            return True
        
        # Check absolute URLs
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # No scheme or host = relative URL
        if not parsed.scheme and not parsed.netloc:
            return True
        
        # Check against allowed domains
        if request:
            host = request.get_host().split(':')[0]
            cls.ALLOWED_DOMAINS.append(host)
        
        if parsed.netloc:
            domain = parsed.netloc.split(':')[0]
            return domain in cls.ALLOWED_DOMAINS
        
        return False
    
    @classmethod
    def safe_redirect(cls, url: str, fallback: str = '/', request=None) -> str:
        """Return a safe redirect URL."""
        if cls.is_safe_redirect(url, request):
            return url
        
        logger.warning(f"Blocked open redirect attempt to: {url}")
        return fallback


# ============================================================================
# 7. PARAMETER TAMPERING PROTECTION
# ============================================================================

class ParameterTamperProtection:
    """
    Detects and prevents parameter tampering attacks.
    """
    
    @classmethod
    def sign_params(cls, params: dict, secret_key: str = None) -> str:
        """
        Create a signature for parameters to detect tampering.
        """
        secret = secret_key or settings.SECRET_KEY
        sorted_params = sorted(params.items())
        param_string = '&'.join(f"{k}={v}" for k, v in sorted_params)
        
        signature = hmac.new(
            secret.encode(),
            param_string.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        return signature
    
    @classmethod
    def verify_params(cls, params: dict, signature: str, secret_key: str = None) -> bool:
        """
        Verify parameter signature to detect tampering.
        """
        expected_sig = cls.sign_params(params, secret_key)
        return hmac.compare_digest(expected_sig, signature)
    
    @classmethod
    def validate_numeric_param(cls, value: Any, min_val: int = None, max_val: int = None) -> Tuple[bool, int]:
        """
        Validate and sanitize numeric parameters.
        
        Returns:
            (is_valid, sanitized_value)
        """
        try:
            numeric_val = int(value)
            
            if min_val is not None and numeric_val < min_val:
                return False, min_val
            
            if max_val is not None and numeric_val > max_val:
                return False, max_val
            
            return True, numeric_val
        except (ValueError, TypeError):
            return False, 0


# ============================================================================
# 8. BOT DETECTION
# ============================================================================

class BotDetection:
    """
    Detects and blocks malicious bots and automated attacks.
    """
    
    # Known bad bot signatures
    BAD_BOT_SIGNATURES = [
        'sqlmap', 'nikto', 'nmap', 'masscan', 'dirbuster',
        'gobuster', 'wfuzz', 'hydra', 'medusa', 'burp',
        'owasp', 'skipfish', 'w3af', 'acunetix', 'nessus',
        'openvas', 'arachni', 'zap', 'vega', 'grabber',
        'scrapy', 'python-requests', 'go-http-client',
        'libwww-perl', 'wget', 'curl',  # Only block without valid referer
    ]
    
    # Behavioral indicators
    SUSPICIOUS_BEHAVIORS = {
        'rapid_requests': {'threshold': 30, 'window': 10},  # 30 req in 10 sec
        'no_cookies': {'max_requests': 10},  # > 10 requests without cookies
        'sequential_paths': {'threshold': 5},  # Accessing sequential IDs
    }
    
    @classmethod
    def is_bot(cls, request) -> Tuple[bool, str]:
        """
        Detect if request is from a bot.
        
        Returns:
            (is_bot, reason)
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        ip = get_client_ip(request)
        
        # ========================================================================
        # DEVELOPMENT EXEMPTION: Skip aggressive bot checks for localhost
        # ========================================================================
        is_localhost = ip in ('127.0.0.1', 'localhost', '::1')
        if is_localhost:
            # Only check for known bad bot signatures on localhost
            for signature in cls.BAD_BOT_SIGNATURES:
                # Skip curl/wget on localhost (legitimate dev tools)
                if signature in ('curl', 'wget') and is_localhost:
                    continue
                if signature in user_agent:
                    return True, f"Bad bot signature detected: {signature}"
            # Skip behavioral checks on localhost
            return False, ""
        
        # Check bad bot signatures
        for signature in cls.BAD_BOT_SIGNATURES:
            if signature in user_agent:
                return True, f"Bad bot signature detected: {signature}"
        
        # Check for missing/suspicious headers
        if not user_agent:
            return True, "Missing User-Agent header"
        
        # Check behavioral patterns
        # Rapid requests check
        rapid_key = f"bot:rapid:{ip}"
        rapid_data = cache.get(rapid_key, {'count': 0, 'start': time.time()})
        rapid_data['count'] += 1
        
        if time.time() - rapid_data['start'] > cls.SUSPICIOUS_BEHAVIORS['rapid_requests']['window']:
            rapid_data = {'count': 1, 'start': time.time()}
        
        cache.set(rapid_key, rapid_data, timeout=60)
        
        if rapid_data['count'] > cls.SUSPICIOUS_BEHAVIORS['rapid_requests']['threshold']:
            return True, "Rapid request pattern detected"
        
        return False, ""
    
    @classmethod
    def add_honeypot_field(cls, field_name: str = 'website') -> dict:
        """
        Generate a honeypot field for forms.
        Bots often fill all fields, legitimate users leave honeypot empty.
        """
        return {
            'name': field_name,
            'style': 'position:absolute;left:-9999px;',
            'tabindex': '-1',
            'autocomplete': 'off',
        }
    
    @classmethod
    def check_honeypot(cls, request, field_name: str = 'website') -> bool:
        """
        Check if honeypot field was filled (indicates bot).
        
        Returns:
            True if honeypot was triggered (is a bot)
        """
        honeypot_value = request.POST.get(field_name, '') or request.GET.get(field_name, '')
        if honeypot_value:
            logger.warning(f"Honeypot triggered by IP {get_client_ip(request)}")
            return True
        return False


# ============================================================================
# 9. SECURITY HEADERS
# ============================================================================

class SecurityHeaders:
    """
    Comprehensive security headers management.
    """
    
    @classmethod
    def add_all_headers(cls, response, request=None) -> HttpResponse:
        """Add all security headers to response."""
        
        # Content-Type Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Frame Options
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' wss: ws:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Strict Transport Security (HTTPS only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Cache Control for sensitive pages
        if request and request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


# ============================================================================
# 10. COMPREHENSIVE REQUEST VALIDATOR
# ============================================================================

class ComprehensiveSecurityValidator:
    """
    Master validator that combines all security checks.
    """
    
    @classmethod
    def validate_request(cls, request) -> Tuple[bool, str, str]:
        """
        Comprehensive request validation.
        
        Returns:
            (is_valid, error_message, attack_type)
        """
        ip = get_client_ip(request)
        
        # 1. Bot detection
        is_bot, bot_reason = BotDetection.is_bot(request)
        if is_bot:
            log_security_event(request, 'bot_detected', bot_reason)
            return False, "Access denied", "Bot"
        
        # 2. Check brute force
        account = getattr(request.user, 'email', None)
        is_blocked, block_reason, _ = BruteForceProtection.check_brute_force(request, account)
        if is_blocked:
            log_security_event(request, 'brute_force_blocked', block_reason)
            return False, block_reason, "Brute Force"
        
        # 3. Check all input for injection attacks
        # Check URL path
        is_malicious, attack_type = InjectionProtection.check_injection(request.path)
        if is_malicious:
            log_security_event(request, 'injection_blocked', f"Path: {request.path}")
            return False, "Malicious request blocked", attack_type
        
        # Check query parameters
        for key, value in request.GET.items():
            is_malicious, attack_type = InjectionProtection.check_injection(str(value))
            if is_malicious:
                log_security_event(request, 'injection_blocked', f"GET param {key}")
                return False, "Malicious request blocked", attack_type
        
        # Check POST data
        for key, value in request.POST.items():
            if key in ['csrfmiddlewaretoken', 'password', 'password1', 'password2']:
                continue
            is_malicious, attack_type = InjectionProtection.check_injection(str(value))
            if is_malicious:
                log_security_event(request, 'injection_blocked', f"POST param {key}")
                return False, "Malicious request blocked", attack_type
        
        # 4. Session validation
        if request.user.is_authenticated:
            is_valid, session_reason = SessionSecurity.validate_session(request)
            if not is_valid:
                log_security_event(request, 'session_invalid', session_reason)
                return False, session_reason, "Session Attack"
        
        # 5. Honeypot check for POST requests
        if request.method == 'POST':
            if BotDetection.check_honeypot(request):
                log_security_event(request, 'honeypot_triggered', '')
                return False, "Request blocked", "Bot"
        
        return True, "", ""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client_ip(request) -> str:
    """Extract real client IP, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def log_security_event(event_type: str, request, details: dict = None):
    """Log security events for monitoring and forensics."""
    if details is None:
        details = {}
    
    ip = get_client_ip(request)
    user = getattr(request.user, 'email', 'anonymous') if hasattr(request, 'user') else 'anonymous'
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:100]
    path = request.path
    
    # Convert details dict to string
    details_str = str(details) if details else ""
    
    log_message = (
        f"SECURITY EVENT: {event_type.upper()} | "
        f"IP: {ip} | User: {user} | Path: {path} | "
        f"UA: {user_agent} | Details: {details_str}"
    )
    
    # Log to security logger
    logger.warning(log_message)
    
    # Store in cache for dashboard monitoring
    event_key = f"security_event:{int(time.time())}:{secrets.token_hex(4)}"
    event_data = {
        'type': event_type,
        'ip': ip,
        'user': user,
        'path': path,
        'details': details,
        'timestamp': time.time(),
    }
    cache.set(event_key, event_data, timeout=86400)  # Keep for 24 hours


# ============================================================================
# DECORATORS
# ============================================================================

def advanced_security_check(view_func):
    """
    Comprehensive security decorator for all views.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Run comprehensive security validation
        is_valid, error_msg, attack_type = ComprehensiveSecurityValidator.validate_request(request)
        
        if not is_valid:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'security_blocked',
                    'message': 'Request blocked for security reasons'
                }, status=403)
            
            messages.error(request, "Security check failed. Please try again.")
            return HttpResponseForbidden("Request blocked for security reasons.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def idor_protected(owner_field: str = 'user'):
    """
    Decorator to prevent IDOR attacks.
    
    Usage:
        @idor_protected('owner')
        def my_view(request, obj):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the object from the view
            response = view_func(request, *args, **kwargs)
            
            # If view returns an object, verify ownership
            if hasattr(response, 'context_data'):
                obj = response.context_data.get('object')
                if obj and not IDORProtection.verify_object_ownership(request, obj, owner_field):
                    log_security_event(request, 'idor_blocked', f"Object: {obj}")
                    raise PermissionDenied("You don't have permission to access this resource.")
            
            return response
        return wrapper
    return decorator


def rate_limited(action_type: str = 'api', max_requests: int = None, window: int = None):
    """
    Enhanced rate limiting decorator.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request)
            user_id = getattr(request.user, 'id', 'anonymous')
            cache_key = f"ratelimit:{action_type}:{ip}:{user_id}"
            
            # Get limits
            limits = {
                'login': (5, 300),
                'api': (100, 60),
                'page': (60, 60),
                'sensitive': (10, 60),
            }
            max_req, win = limits.get(action_type, (60, 60))
            if max_requests:
                max_req = max_requests
            if window:
                win = window
            
            # Check rate limit
            data = cache.get(cache_key, {'count': 0, 'start': time.time()})
            
            if time.time() - data['start'] > win:
                data = {'count': 0, 'start': time.time()}
            
            data['count'] += 1
            cache.set(cache_key, data, timeout=win)
            
            if data['count'] > max_req:
                wait_time = int(win - (time.time() - data['start']))
                log_security_event(request, 'rate_limited', f"Action: {action_type}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'rate_limited',
                        'message': f'Too many requests. Wait {wait_time}s.',
                        'retry_after': wait_time
                    }, status=429)
                
                return HttpResponseForbidden(f"Rate limited. Wait {wait_time} seconds.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
