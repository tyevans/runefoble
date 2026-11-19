"""AWS Signature Version 4 headers for Silo S3 requests.

Silo (Chainguard MinIO) refuses unsigned requests with 403. The signature comes from
botocore. This module holds no hand-written crypto (TASK-0926).
"""

from __future__ import annotations

from botocore.auth import S3SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

SILO_SIGNING_SERVICE = "s3"


def sigv4_headers(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes,
    access_key: str,
    secret_key: str,
    region: str,
) -> dict[str, str]:
    """Return `headers` plus the SigV4 `Authorization`, `X-Amz-Date` and payload hash headers.

    Send the request with exactly this URL, body and header set, or the signature fails.
    """
    request = AWSRequest(method=method, url=url, data=body, headers=headers)
    S3SigV4Auth(Credentials(access_key, secret_key), SILO_SIGNING_SERVICE, region).add_auth(request)
    return dict(request.headers.items())
