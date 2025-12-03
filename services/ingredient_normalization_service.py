"""
Ingredient Normalization Service

AI-powered service to normalize raw ingredient text into structured data.
This is an optional, on-demand feature (not automatic).
"""
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core.settings import settings

logger = logging.getLogger(__name__)


class NormalizedIngredient(BaseModel):
    """Result of ingredient normalization"""
    normalized_name: str = Field(..., description="Clean ingredient name")
    category: Optional[str] = Field(None, description="Food category")
    quantity: Optional[float] = Field(None, description="Extracted quantity")
    unit: Optional[str] = Field(None, description="Extracted unit")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence")
    notes: Optional[str] = Field(None, description="Additional observations")


class IngredientNormalizationService:
    """Service for AI-powered ingredient normalization"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = "gpt-4o-mini"  # Use cheaper model for text tasks

    async def normalize_ingredient(
        self,
        raw_text: str,
    ) -> NormalizedIngredient:
        """
        Normalize raw ingredient text using AI.

        Args:
            raw_text: Raw ingredient text (e.g., "2 lbs fresh tomatoes")

        Returns:
            NormalizedIngredient with structured data

        Raises:
            Exception: If API call fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        logger.info(f"Normalizing ingredient: {raw_text}")

        try:
            prompt = self._build_normalization_prompt(raw_text)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at parsing and normalizing ingredient text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.1,  # Low temperature for consistency
            )

            result = self._parse_ai_response(response)
            logger.info(f"Normalized to: {result.normalized_name}")

            return result

        except Exception as e:
            logger.error(f"Ingredient normalization failed: {e}", exc_info=True)
            raise

    def _build_normalization_prompt(self, raw_text: str) -> str:
        """Build prompt for ingredient normalization"""
        return f"""
Parse and normalize this ingredient text: "{raw_text}"

Extract and return:
1. **normalized_name**: Clean ingredient name (singular form, no adjectives like "fresh")
   - Examples: "tomato", "chicken breast", "olive oil"
2. **category**: Food category from this list:
   - Produce, Dairy, Meat, Bakery, Pantry, Frozen, Beverages, Snacks, Condiments, Other
3. **quantity**: Numeric quantity if present (null if none)
4. **unit**: Unit of measurement if present (null if none)
   - Standardize to: lb, oz, g, kg, cup, tbsp, tsp, ml, l, gallon, each, count
5. **confidence**: How confident you are (0.0 to 1.0)
6. **notes**: Any important observations (optional)

Return JSON format:
{{
  "normalized_name": "tomato",
  "category": "Produce",
  "quantity": 2.0,
  "unit": "lb",
  "confidence": 0.95,
  "notes": null
}}

IMPORTANT:
- Focus on the core ingredient, remove descriptors
- Use singular form for ingredient name
- If quantity/unit unclear, set to null with note
- Be conservative with confidence scores
"""

    def _parse_ai_response(self, response) -> NormalizedIngredient:
        """Parse OpenAI response into NormalizedIngredient"""
        import json

        try:
            content = response.choices[0].message.content

            # Handle markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            # Parse JSON
            data = json.loads(content)

            return NormalizedIngredient(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Response: {response.choices[0].message.content}")

            # Fallback: return raw text with low confidence
            return NormalizedIngredient(
                normalized_name=content[:100],  # Truncate
                category="Other",
                quantity=None,
                unit=None,
                confidence=0.0,
                notes=f"Failed to parse: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error parsing response: {e}", exc_info=True)
            raise

    async def normalize_batch(
        self,
        raw_texts: list[str],
    ) -> list[NormalizedIngredient]:
        """
        Normalize multiple ingredients in batch (for efficiency).

        Args:
            raw_texts: List of raw ingredient texts

        Returns:
            List of NormalizedIngredient results
        """
        import asyncio

        tasks = [self.normalize_ingredient(text) for text in raw_texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        normalized = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch normalization failed for '{raw_texts[i]}': {result}")
                # Add fallback result
                normalized.append(NormalizedIngredient(
                    normalized_name=raw_texts[i][:100],
                    category="Other",
                    quantity=None,
                    unit=None,
                    confidence=0.0,
                    notes=f"Error: {str(result)}"
                ))
            else:
                normalized.append(result)

        return normalized


# Singleton instance
ingredient_normalization_service = IngredientNormalizationService()
