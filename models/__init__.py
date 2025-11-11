# models/__init__.py
from core.db import Base  # noqa: F401
from .meal import Meal  # noqa: F401


# Identity
from .user import User  # noqa: F401
from .family import Family  # noqa: F401
from .membership import FamilyMembership  # noqa: F401

# Reference / Catalog
from .unit import Unit  # noqa: F401
from .ingredient import Ingredient  # noqa: F401
from .diet_tag import DietTag  # noqa: F401

# Recipes
from .recipe import Recipe  # noqa: F401
from .recipe_ingredient import RecipeIngredient  # noqa: F401
# from .recipe_diet_tag import RecipeDietTag  # noqa: F401  # if you have it

# Planning
from .meal_plan import MealPlan, MealSlot, MealSlotMeal  # noqa: F401

# Inventory & Grocery
from .pantry_item import PantryItem  # noqa: F401
from .grocery_list import GroceryList, GroceryListItem  # noqa: F401

# Personalization
from .user_preference import UserPreference  # noqa: F401

# Chat
from .chat import ChatConversation, ChatMessage  # noqa: F401
from .oauth_account import OAuthAccount  # noqa: F401
