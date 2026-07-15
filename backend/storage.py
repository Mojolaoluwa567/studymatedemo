"""
Object storage for original uploaded files (currently: PDFs), backed by
Cloudflare R2 (S3-compatible). Replaces storing raw file bytes directly
in Postgres rows, which was eating through Render's database storage
quota fast (a handful of PDF uploads could fill a free-tier database).
"""
import os
import logging
import boto3
from botocore.config import Config

_client = None


def get_storage_client():
    global _client
    if _client is None:
        account_id = os.environ.get("R2_ACCOUNT_ID")
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "studymate-documents")


def upload_file(file_bytes, storage_key, content_type="application/pdf"):
    """Uploads bytes to R2 under the given key. Raises on failure -
    caller decides how to handle (e.g. still save the document without
    the original file, just no Read-tab PDF view for it)."""
    get_storage_client().put_object(
        Bucket=BUCKET_NAME,
        Key=storage_key,
        Body=file_bytes,
        ContentType=content_type,
    )


def get_presigned_url(storage_key, expires_in=300):
    """Returns a temporary signed URL the browser can fetch directly -
    avoids proxying file bytes through the Flask server (saves memory
    and bandwidth on Render). Expires quickly since it's only used to
    load the PDF viewer immediately after being requested."""
    return get_storage_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": storage_key},
        ExpiresIn=expires_in,
    )


def delete_file(storage_key):
    """Best-effort delete - if this fails, log it but don't block the
    document row itself from being deleted."""
    try:
        get_storage_client().delete_object(Bucket=BUCKET_NAME, Key=storage_key)
    except Exception as e:
        logging.warning(f"Failed to delete {storage_key} from storage: {e}")