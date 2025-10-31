"""
Pantry Item Image Service - Handles automatic image generation and storage for pantry items
"""
import logging
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
import httpx
import re
from io import BytesIO

from core.settings import settings
from core.supaBase_client import get_supabase_admin
from models.pantry_item import PantryItem
from models.user import User
from services.chat_service import chat_service

logger = logging.getLogger(__name__)


class PantryImageService:
    """Service for generating and storing pantry item images"""

    def __init__(self):
        self.supabase = get_supabase_admin()
        self.bucket_name = "pantry_items"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize item name for use as filename"""
        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name.strip())
        sanitized = re.sub(r'[\s_-]+', '_', sanitized)
        return sanitized.lower()

    def _generate_storage_path(self, user_id: int, item_id: int, item_name: str) -> str:
        """Generate storage path for pantry item image"""
        sanitized_name = self._sanitize_filename(item_name)
        return f"{user_id}/{item_id}/{sanitized_name}.jpg"

    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL and return as bytes"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    def _upload_to_supabase(self, file_path: str, image_data: bytes) -> str:
        """Upload image to Supabase storage and return public URL"""
        try:
            # Upload file to storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=image_data,
                file_options={"content-type": "image/jpeg"}
            )
            
            if result.error:
                raise Exception(f"Supabase upload error: {result.error}")
            
            # Get public URL
            public_url_result = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            return public_url_result
            
        except Exception as e:
            logger.error(f"Failed to upload image to Supabase: {e}")
            raise

    async def generate_and_store_image(
        self, 
        db: Session, 
        user: User, 
        pantry_item: PantryItem,
        item_name: str
    ) -> Optional[str]:
        """
        Generate an image for a pantry item and store it in Supabase
        
        Args:
            db: Database session
            user: User who owns the pantry item
            pantry_item: The pantry item instance
            item_name: Name of the ingredient/item
            
        Returns:
            Public URL of the generated image, or None if generation failed
        """
        try:
            # Generate a food-focused prompt for the item
            prompt = f"A single {item_name}, fresh and appetizing, on a clean white background, professional food photography style, high quality, well-lit"
            
            # Generate image using existing chat service
            from schemas.chat import ImageGenerationRequest
            
            image_request = ImageGenerationRequest(
                prompt=prompt,
                size="512x512",  # Smaller size for pantry items
                quality="standard",
                style="natural"
            )
            
            # Generate image (this will create a conversation, but that's okay for tracking)
            result = await chat_service.generate_image(db, user, image_request)
            
            # Download the generated image
            image_data = await self._download_image(result.image_url)
            
            # Generate storage path
            storage_path = self._generate_storage_path(
                user.id, 
                pantry_item.id, 
                item_name
            )
            
            # Upload to Supabase
            public_url = self._upload_to_supabase(storage_path, image_data)
            
            # Update pantry item with image URL
            pantry_item.image_url = public_url
            db.commit()
            
            logger.info(f"Generated and stored image for pantry item {pantry_item.id}: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to generate image for pantry item {pantry_item.id}: {e}")
            db.rollback()
            return None

    async def generate_image_background(
        self, 
        db: Session, 
        user: User, 
        pantry_item: PantryItem,
        item_name: str
    ):
        """
        Generate image in background (fire-and-forget)
        This is useful when you don't want to block the pantry item creation
        """
        try:
            await self.generate_and_store_image(db, user, pantry_item, item_name)
        except Exception as e:
            logger.error(f"Background image generation failed for pantry item {pantry_item.id}: {e}")

    def delete_image(self, user_id: int, item_id: int, item_name: str) -> bool:
        """Delete image from Supabase storage"""
        try:
            storage_path = self._generate_storage_path(user_id, item_id, item_name)
            result = self.supabase.storage.from_(self.bucket_name).remove([storage_path])
            
            if result.error:
                logger.error(f"Failed to delete image: {result.error}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False


# Global service instance
pantry_image_service = PantryImageService()
