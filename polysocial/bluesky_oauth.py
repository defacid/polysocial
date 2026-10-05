"""AT Protocol OAuth helpers for Polysocial.

Implements the public-client flow required by Bluesky: handle resolution,
PAR + PKCE, and DPoP-bound token/resource requests.  Tokens and private keys
are encrypted by ``CredentialVault`` before they are persisted.
"""

import base64
import hashlib
import ipaddress
import json
import re
import secrets
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils


SCOPE = "atproto repo:app.bsky.feed.post?action=create"
HANDLE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", re.I)


class BlueskyOAuthError(RuntimeError):
    pass


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _json(response):
    return json.loads(response.read().decode("utf-8"))


def _safe_https(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port is not None:
        return False
    try:
        ipaddress.ip_address(parts.hostname)
        return False
    except ValueError:
        return "." in parts.hostname and not parts.hostname.endswith((".local", ".internal", ".localhost"))


def _base_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _private_key():
    return ec.generate_private_key(ec.SECP256R1())


def _key_to_pem(key):
    return _b64(key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def _key_from_pem(value):
    return serialization.load_der_private_key(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)), password=None)


def _public_jwk(key):
    numbers = key.public_key().public_numbers()
    return {"kty": "EC", "crv": "P-256", "x": _b64(numbers.x.to_bytes(32, "big")), "y": _b64(numbers.y.to_bytes(32, "big"))}


def _jwt(key, payload):
    header = {"typ": "dpop+jwt", "alg": "ES256", "jwk": _public_jwk(key)}
    signed = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}".encode()
    der = key.sign(signed, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der)
    return signed.decode() + "." + _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def _dpop(key, method, url, access_token=None, nonce=None):
    payload = {"jti": secrets.token_urlsafe(20), "htm": method.upper(), "htu": _base_url(url), "iat": int(time.time())}
    if access_token:
        payload["ath"] = _b64(hashlib.sha256(access_token.encode()).digest())
    if nonce:
        payload["nonce"] = nonce
    return _jwt(key, payload)


def _request(method, url, body=None, headers=None, key=None, access_token=None, nonce=None):
    headers = {"Accept": "application/json", **(headers or {})}
    if key:
        headers["DPoP"] = _dpop(key, method, url, access_token, nonce)
    if access_token:
        headers["Authorization"] = f"DPoP {access_token}"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), _json(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail)
        except json.JSONDecodeError:
            pass
        return error.code, dict(error.headers.items()), detail
    except OSError as error:
        raise BlueskyOAuthError(f"Could not reach Bluesky: {error}") from error


def _metadata(url):
    if not _safe_https(url):
        raise BlueskyOAuthError("Bluesky returned an unsafe OAuth endpoint")
    status, _, value = _request("GET", url)
    if status != 200 or not isinstance(value, dict):
        raise BlueskyOAuthError("Could not retrieve Bluesky OAuth metadata")
    required = ("issuer", "authorization_endpoint", "token_endpoint", "pushed_authorization_request_endpoint")
    if any(not value.get(key) or not _safe_https(value[key]) for key in required):
        raise BlueskyOAuthError("Bluesky returned invalid OAuth metadata")
    return value


def _resolve(handle):
    handle = handle.strip().lstrip("@").lower()
    if not HANDLE.fullmatch(handle):
        raise BlueskyOAuthError("Enter a valid Bluesky handle")
    status, _, identity = _request("GET", "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?" + urlencode({"handle": handle}))
    if status != 200 or not isinstance(identity, dict) or not identity.get("did"):
        raise BlueskyOAuthError("Could not resolve that Bluesky handle")
    did = identity["did"]
    if not did.startswith("did:plc:"):
        raise BlueskyOAuthError("Only did:plc Bluesky accounts are currently supported")
    status, _, document = _request("GET", f"https://plc.directory/{did}")
    if status != 200 or not isinstance(document, dict):
        raise BlueskyOAuthError("Could not resolve the Bluesky account")
    pds = next((service.get("serviceEndpoint") for service in document.get("service", []) if service.get("id") == "#atproto_pds"), None)
    if not _safe_https(pds or ""):
        raise BlueskyOAuthError("Bluesky account has no valid PDS endpoint")
    return handle, did, pds.rstrip("/")


def start(handle, client_id, redirect_uri):
    """Create a PAR request and return state that must be stored server-side."""
    handle, did, pds = _resolve(handle)
    status, _, resource = _request("GET", pds + "/.well-known/oauth-protected-resource")
    servers = resource.get("authorization_servers", []) if isinstance(resource, dict) else []
    if status != 200 or not servers or not _safe_https(servers[0]):
        raise BlueskyOAuthError("Could not find the Bluesky authorization server")
    metadata = _metadata(servers[0].rstrip("/") + "/.well-known/oauth-authorization-server")
    key = _private_key()
    verifier = _b64(secrets.token_bytes(48))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(32)
    form = urlencode({"client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri, "scope": SCOPE, "state": state, "login_hint": handle, "code_challenge": challenge, "code_challenge_method": "S256"}).encode()
    status, headers, payload = _request("POST", metadata["pushed_authorization_request_endpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key)
    if status == 400 and headers.get("DPoP-Nonce"):
        status, headers, payload = _request("POST", metadata["pushed_authorization_request_endpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key, nonce=headers["DPoP-Nonce"])
    if status not in (200, 201) or not isinstance(payload, dict) or not payload.get("request_uri"):
        raise BlueskyOAuthError("Bluesky could not start authorization")
    return {"state": state, "did": did, "handle": handle, "pds": pds, "issuer": metadata["issuer"], "tokenEndpoint": metadata["token_endpoint"], "authorizationEndpoint": metadata["authorization_endpoint"], "requestUri": payload["request_uri"], "verifier": verifier, "key": _key_to_pem(key), "nonce": headers.get("DPoP-Nonce", "")}


def finish(pending, code, issuer, client_id, redirect_uri):
    if issuer != pending.get("issuer") or not code:
        raise BlueskyOAuthError("Bluesky returned an invalid authorization response")
    key = _key_from_pem(pending["key"])
    form = urlencode({"client_id": client_id, "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "code_verifier": pending["verifier"]}).encode()
    status, headers, payload = _request("POST", pending["tokenEndpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key, nonce=pending.get("nonce"))
    if status == 400 and headers.get("DPoP-Nonce"):
        status, headers, payload = _request("POST", pending["tokenEndpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key, nonce=headers["DPoP-Nonce"])
    if status not in (200, 201) or not isinstance(payload, dict) or payload.get("sub") != pending["did"] or not payload.get("access_token") or not payload.get("refresh_token"):
        raise BlueskyOAuthError("Bluesky did not return valid OAuth tokens")
    return {"auth": "oauth", "handle": pending["handle"], "did": pending["did"], "service": pending["pds"], "issuer": pending["issuer"], "tokenEndpoint": pending["tokenEndpoint"], "accessToken": payload["access_token"], "refreshToken": payload["refresh_token"], "dpopKey": pending["key"], "dpopNonce": "", "tokenNonce": headers.get("DPoP-Nonce", ""), "expiresIn": payload.get("expires_in")}


def refresh(credentials):
    key = _key_from_pem(credentials["dpopKey"])
    form = urlencode({"client_id": credentials["clientId"], "grant_type": "refresh_token", "refresh_token": credentials["refreshToken"]}).encode()
    status, headers, payload = _request("POST", credentials["tokenEndpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key, nonce=credentials.get("tokenNonce"))
    if status == 400 and headers.get("DPoP-Nonce"):
        status, headers, payload = _request("POST", credentials["tokenEndpoint"], form, {"Content-Type": "application/x-www-form-urlencoded"}, key, nonce=headers["DPoP-Nonce"])
    if status not in (200, 201) or not isinstance(payload, dict) or not payload.get("access_token") or not payload.get("refresh_token"):
        raise BlueskyOAuthError("Bluesky OAuth connection must be renewed")
    credentials.update({"accessToken": payload["access_token"], "refreshToken": payload["refresh_token"], "tokenNonce": headers.get("DPoP-Nonce", ""), "expiresIn": payload.get("expires_in")})
    return credentials


def dpop_headers(credentials, method, url):
    key = _key_from_pem(credentials["dpopKey"])
    return {"Authorization": f"DPoP {credentials['accessToken']}", "DPoP": _dpop(key, method, url, credentials["accessToken"], credentials.get("dpopNonce"))}


def resource_request(credentials, method, url, body=None, headers=None):
    """Make a DPoP-bound PDS request and retain a rotated resource nonce."""
    key = _key_from_pem(credentials["dpopKey"])
    status, response_headers, payload = _request(method, url, body, headers, key, credentials["accessToken"], credentials.get("dpopNonce"))
    nonce = response_headers.get("DPoP-Nonce")
    if status in (400, 401) and nonce:
        status, response_headers, payload = _request(method, url, body, headers, key, credentials["accessToken"], nonce)
        nonce = response_headers.get("DPoP-Nonce", nonce)
    if nonce:
        credentials["dpopNonce"] = nonce
    if status not in (200, 201):
        raise BlueskyOAuthError(f"Bluesky returned {status}: {json.dumps(payload)[:500]}")
    return payload
