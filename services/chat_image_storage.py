"""
Chat Image Storage Service - Handles uploading and managing chat images in Supabase Storage
"""
import logging
import base64
import uuid
from typing import Optional, Tuple

from core.settings import settings
from core.supaBase_client import get_supabase_admin

logger = logging.getLogger(__name__)

CHAT_IMAGES_BUCKET = "chat-images"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


class ChatImageStorageService:
    """Service for uploading and managing chat images in Supabase Storage"""

    def __init__(self):
        self._supabase = None

    @property
    def supabase(self):
        """Lazy initialization of Supabase client"""
        if self._supabase is None:
            self._supabase = get_supabase_admin()
        return self._supabase

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_to_ext = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }
        return mime_to_ext.get(mime_type, "jpg")

    def _generate_storage_path(
        self,
        user_id: int,
        conversation_id: int,
        message_id: int,
        extension: str
    ) -> str:
        """
        Generate storage path for chat image.
        Format: {user_id}/{conversation_id}/{message_id}.{ext}
        """
        return f"{user_id}/{conversation_id}/{message_id}.{extension}"

    def _generate_temp_storage_path(
        self,
        user_id: int,
        conversation_id: int,
        extension: str
    ) -> str:
        """
        Generate temporary storage path before message_id is known.
        Uses UUID for uniqueness.
        Format: {user_id}/{conversation_id}/{uuid}.{ext}
        """
        unique_id = str(uuid.uuid4())
        return f"{user_id}/{conversation_id}/{unique_id}.{extension}"

    def upload_image(
        self,
        image_base64: str,
        mime_type: str,
        user_id: int,
        conversation_id: int,
        message_id: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload a base64-encoded image to Supabase Storage.

        Args:
            image_base64: Base64-encoded image data (without data URL prefix)
            mime_type: MIME type of the image (image/jpeg, image/png, image/webp)
            user_id: ID of the user uploading the image
            conversation_id: ID of the conversation
            message_id: Optional message ID (if known)

        Returns:
            Tuple of (public_url, storage_path) on success, (None, None) on failure
        """
        try:
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_base64)
            except Exception as e:
                logger.error(f"CHAT_IMAGE_DECODE_ERROR | error={e}")
                return None, None

            # Validate size
            if len(image_bytes) > MAX_IMAGE_SIZE:
                logger.error(
                    f"CHAT_IMAGE_TOO_LARGE | size={len(image_bytes)} | max={MAX_IMAGE_SIZE}"
                )
                return None, None

            # Get file extension
            extension = self._get_extension_from_mime(mime_type)

            # Generate storage path
            if message_id:
                storage_path = self._generate_storage_path(
                    user_id, conversation_id, message_id, extension
                )
            else:
                storage_path = self._generate_temp_storage_path(
                    user_id, conversation_id, extension
                )

            # Upload to Supabase Storage
            result = self.supabase.storage.from_(CHAT_IMAGES_BUCKET).upload(
                path=storage_path,
                file=image_bytes,
                file_options={
                    "content-type": mime_type,
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )

            # Check for upload error
            if isinstance(result, dict) and result.get("error"):
                error_msg = result["error"].get("message", str(result["error"]))
                logger.error(f"CHAT_IMAGE_UPLOAD_ERROR | error={error_msg}")
                return None, None

            # Get public URL
            public_url_result = self.supabase.storage.from_(CHAT_IMAGES_BUCKET).get_public_url(storage_path)
            public_url = self._extract_public_url(public_url_result)

            if not public_url:
                logger.error("CHAT_IMAGE_URL_ERROR | Failed to get public URL")
                return None, None

            logger.info(
                f"CHAT_IMAGE_UPLOAD_SUCCESS | user_id={user_id} | "
                f"conversation_id={conversation_id} | path={storage_path}"
            )
            return public_url, storage_path

        except Exception as e:
            logger.error(f"CHAT_IMAGE_UPLOAD_FAILED | error={e}", exc_info=True)
            return None, None

    def _extract_public_url(self, result) -> Optional[str]:
        """Extract public URL from Supabase response (handles different return formats)"""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            data = result.get("data") or {}
            return (
                data.get("publicUrl") or
                result.get("publicUrl") or
                result.get("url") or
                ""
            )
        return None

    def delete_image(self, storage_path: str) -> bool:
        """
        Delete an image from Supabase Storage.

        Args:
            storage_path: The storage path of the image to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = self.supabase.storage.from_(CHAT_IMAGES_BUCKET).remove([storage_path])

            if isinstance(result, dict) and result.get("error"):
                error_msg = result["error"].get("message", str(result["error"]))
                logger.error(f"CHAT_IMAGE_DELETE_ERROR | path={storage_path} | error={error_msg}")
                return False

            logger.info(f"CHAT_IMAGE_DELETE_SUCCESS | path={storage_path}")
            return True

        except Exception as e:
            logger.error(f"CHAT_IMAGE_DELETE_FAILED | path={storage_path} | error={e}")
            return False


# Global service instance
chat_image_storage = ChatImageStorageService()
