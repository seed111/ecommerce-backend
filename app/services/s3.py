import os
import uuid
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
_s3 = None


def get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=AWS_REGION)
    return _s3


def upload_product_image(file_bytes, content_type, product_id):
    key = f"products/{product_id}/{uuid.uuid4()}"
    try:
        get_s3().put_object(Bucket=BUCKET_NAME, Key=key, Body=file_bytes, ContentType=content_type)
        return key
    except ClientError as e:
        logger.error(f"S3 upload failed: {e.response['Error']}")
        raise


def generate_presigned_url(object_key, expiry_seconds=3600):
    try:
        return get_s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": object_key},
            ExpiresIn=expiry_seconds,
        )
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e.response['Error']}")
        raise