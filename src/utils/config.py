"""
Configuration Module for SupportPilot

This module handles environment variable loading and validation.
It ensures critical API keys are present before the application starts.

Usage:
    from src.utils.config import check_env_vars
    check_env_vars()  # Raises ValueError if GOOGLE_API_KEY is missing

Environment Variables Required:
    - GOOGLE_API_KEY: API key for Google Gemini models

Author: SupportPilot Team
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
load_dotenv()


def check_env_vars() -> bool:
    """
    Validates that all required environment variables are set.
    
    This function checks for the presence of GOOGLE_API_KEY, which is
    mandatory for the Google ADK to authenticate API requests to Gemini models.
    
    Returns:
        bool: True if all required variables are present.
    
    Raises:
        ValueError: If GOOGLE_API_KEY is not found in environment variables.
    
    Example:
        >>> check_env_vars()
        True
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError(
            "❌ GOOGLE_API_KEY not found in environment variables.\n"
            "   Please create a .env file in the project root with:\n"
            "   GOOGLE_API_KEY=your_api_key_here\n"
            "   Get your API key at: https://aistudio.google.com/apikey"
        )
    
    return True