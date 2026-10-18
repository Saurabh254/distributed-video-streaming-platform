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
    """Manages S3 / MinIO client for playback manifest inspection and access."""

    def __init__(self) -> None:
        self._client: Any = None
        self._public_client: Any = None

    def start(self) -> None:
        """Initialize boto3 S3 client."""
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

    def generate_presigned_get_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned GET URL for streaming manifest or segments."""
        if self._public_client is None:
            raise RuntimeError("S3 public client not initialized")
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )


s3_manager = S3Manager()
