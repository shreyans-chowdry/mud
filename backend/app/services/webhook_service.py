import hashlib
import hmac
import json
import time
from urllib.parse import urlparse


def encode_payload(payload):
    return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()


def signature(secret, timestamp, request_id, key, body):
    message = f'{timestamp}.{request_id}.{key}.'.encode()+body
    return 'v1='+hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(secret, timestamp, request_id, key, body, supplied, now=None, window=300):
    try:
        stamp = int(timestamp)
    except (ValueError, TypeError):
        return False
    if abs((int(time.time()) if now is None else now)-stamp) > window:
        return False
    expected = signature(secret, stamp, request_id, key, body)
    return hmac.compare_digest(expected, supplied)


def validate_destination(settings):
    if not settings.webhook_url or not settings.webhook_secret:
        raise ValueError('webhook URL and secret must be configured')
    parsed = urlparse(settings.webhook_url)
    if parsed.hostname not in settings.webhook_allow_hosts or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('webhook destination not allowlisted')
    if parsed.scheme != 'https' and not (settings.environment == 'local' and parsed.scheme == 'http'):
        raise ValueError('HTTPS required outside local environment')
    return settings.webhook_url
