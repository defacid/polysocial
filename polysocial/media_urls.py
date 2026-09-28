"""Short-lived, tamper-resistant URLs that let social APIs fetch queued media."""

import hashlib
import hmac
import time
from urllib.parse import quote, urlencode


def signature(secret, post_id, index, expires):
    message = f"{post_id}:{index}:{expires}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def signed_url(origin, secret, post_id, index, lifetime=7200):
    expires = int(time.time()) + lifetime
    query = urlencode({"expires": expires, "signature": signature(secret, post_id, index, expires)})
    return f"{origin.rstrip('/')}/api/media/{quote(post_id)}/{index}?{query}"


def valid_signature(secret, post_id, index, expires, supplied):
    try:
        return int(expires) >= int(time.time()) and hmac.compare_digest(signature(secret, post_id, index, int(expires)), supplied)
    except (TypeError, ValueError):
        return False
