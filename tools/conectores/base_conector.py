import re
import ipaddress
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    'github.com',
    'dev.azure.com',
    'gitlab.com'
]
BLOCKED_IPS = [
    '169.254.169.254', # AWS/Azure metadata
]
PRIVATE_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16')
]

def is_safe_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Check blocked IPs
        try:
            ip = ipaddress.ip_address(hostname)
            if any(ip in net for net in PRIVATE_NETWORKS):
                return False
            if hostname in BLOCKED_IPS:
                return False
        except ValueError:
            # Not an IP, check domain
            domain = hostname.lower()
            if not any(domain == allowed or domain.endswith('.' + allowed) for allowed in ALLOWED_DOMAINS):
                return False
        return True
    except Exception:
        return False

def safe_requests_get(requests, url, *args, **kwargs):
    if not is_safe_url(url):
        raise ValueError(f"URL bloqueada por política de segurança SSRF: {url}")
    return requests.get(url, *args, **kwargs)
