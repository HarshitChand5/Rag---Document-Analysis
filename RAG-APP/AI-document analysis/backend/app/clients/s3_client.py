# s3_client.py — AWS S3 operations for document storage

from __future__ import annotations

import logging
from typing import Optional

import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from app.config import get_settings  # type: ignore

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3_client():
    """Lazy-initialize the S3 client."""
    global _s3_client
    if _s3_client is None:
        settings = get_settings()
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        logger.info("S3 client initialized (region=%s, bucket=%s)", settings.AWS_REGION, settings.AWS_S3_BUCKET)
    return _s3_client


def _bucket() -> str:
    return get_settings().AWS_S3_BUCKET


def make_s3_key(project_id: str, filename: str) -> str:
    """Build the S3 object key for a document."""
    return f"projects/{project_id}/documents/{filename}"


def upload_file(project_id: str, filename: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file to S3.

    Returns the S3 key on success.
    """
    s3_key = make_s3_key(project_id, filename)
    try:
        _get_s3_client().put_object(
            Bucket=_bucket(),
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info("Uploaded to S3: s3://%s/%s (%d bytes)", _bucket(), s3_key, len(file_bytes))
        return s3_key
    except ClientError as exc:
        logger.error("S3 upload failed for %s: %s", s3_key, exc)
        raise


def generate_presigned_url(s3_key: str, expiry: Optional[int] = None) -> str:
    """
    Generate a presigned URL for downloading a file from S3.

    Args:
        s3_key: The S3 object key.
        expiry: URL expiry in seconds (default from settings).
    """
    settings = get_settings()
    if expiry is None:
        expiry = settings.SIGNED_URL_EXPIRY
    try:
        url = _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": s3_key},
            ExpiresIn=expiry,
        )
        return url
    except ClientError as exc:
        logger.error("Failed to generate presigned URL for %s: %s", s3_key, exc)
        raise


def delete_file(s3_key: str) -> bool:
    """
    Delete a file from S3.

    Returns True on success, False on failure.
    """
    try:
        _get_s3_client().delete_object(Bucket=_bucket(), Key=s3_key)
        logger.info("Deleted from S3: s3://%s/%s", _bucket(), s3_key)
        return True
    except ClientError as exc:
        logger.error("S3 delete failed for %s: %s", s3_key, exc)
        return False
