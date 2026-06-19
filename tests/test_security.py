"""Webhook signature verification and private-key normalization.

These guard the GitHub App's trust boundary: a regression here either lets
forged webhooks through or breaks App authentication entirely.
"""

import hashlib
import hmac

from janett.api.routes_github import _verify_signature
from janett.config import Settings


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_passes():
    body = b'{"action":"opened"}'
    assert _verify_signature("s3cret", body, _sign("s3cret", body))


def test_wrong_secret_fails():
    body = b'{"action":"opened"}'
    assert not _verify_signature("s3cret", body, _sign("attacker", body))


def test_tampered_body_fails():
    sig = _sign("s3cret", b"original")
    assert not _verify_signature("s3cret", b"tampered", sig)


def test_missing_signature_fails():
    assert not _verify_signature("s3cret", b"x", None)


def test_wrong_prefix_fails():
    body = b"x"
    digest = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert not _verify_signature("s3cret", body, digest)  # no "sha256=" prefix
    assert not _verify_signature("s3cret", body, "sha1=" + digest)


def test_normalized_private_key_unescapes_newlines():
    # Env vars often carry the PEM with literal "\n" instead of real newlines.
    s = Settings(github_private_key="-----BEGIN-----\\nbody\\n-----END-----")
    assert s.normalized_private_key == "-----BEGIN-----\nbody\n-----END-----"


def test_github_configured_requires_all_three():
    assert not Settings(
        github_app_id="1", github_private_key="", github_webhook_secret=""
    ).github_configured
    assert Settings(
        github_app_id="1", github_private_key="k", github_webhook_secret="s"
    ).github_configured
