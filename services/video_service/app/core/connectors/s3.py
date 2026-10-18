import asyncio
import logging
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Manager:
    """Manages S3 / MinIO client operations and bucket initialization."""

    def __init__(self) -> None:
        self._client: Any = None
        self._public_client: Any = None

    def start(self) -> None:
        """Initialize boto3 S3 clients."""
        if self._client is not None:
            return

        cfg = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3, "mode": "standard"},
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=cfg,
        )

        # Separate client for generating client-accessible presigned URLs if needed
        if settings.s3_public_endpoint_url != settings.s3_endpoint_url:
            self._public_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_public_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=cfg,
            )
        else:
            self._public_client = self._client

        logger.info(
            "S3 client initialized (endpoint=%s, public_endpoint=%s)",
            settings.s3_endpoint_url,
            settings.s3_public_endpoint_url,
        )

    def get_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("S3 client has not been initialized")
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def validate_connection(self) -> bool:
        """Validate connection by listing buckets."""
        client = self.get_client()
        await asyncio.to_thread(client.list_buckets)
        return True

    async def ensure_bucket_and_cors(self, bucket: str) -> None:
        """Ensure the target bucket exists and has browser CORS enabled."""
        client = self.get_client()

        def _check_and_configure():
            # Check bucket existence
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code in ("404", "NoSuchBucket"):
                    logger.info("Creating S3 bucket: %s", bucket)
                    client.create_bucket(Bucket=bucket)
                else:
                    raise

            # Configure CORS for browser direct uploads
            cors_config = {
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "POST", "HEAD", "DELETE"],
                        "AllowedOrigins": ["*"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            }
            client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)
            logger.info("CORS configuration verified on bucket '%s'", bucket)

        await asyncio.to_thread(_check_and_configure)

    def generate_presigned_put_url(
        self,
        bucket: str,
        key: str,
        content_type: str,
        expires_in: int | None = None,
    ) -> str:
        """
        Generate a presigned PUT URL for browser direct upload.
        HMAC signature calculation is local CPU operation.
        """
        if self._public_client is None:
            raise RuntimeError("S3 public client has not been initialized")

        expires = expires_in or settings.s3_presigned_expiry_seconds
        url = self._public_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires,
        )
        return url

    async def head_object(self, bucket: str, key: str) -> dict[str, Any] | None:
        """Check if an object exists in S3 and retrieve its metadata."""
        client = self.get_client()

        def _head():
            try:
                return client.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey"):
                    return None
                raise

        return await asyncio.to_thread(_head)


s3_manager = S3Manager()
