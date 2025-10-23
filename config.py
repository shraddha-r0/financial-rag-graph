"""Configuration settings for the application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Model Configuration
DEFAULT_MODEL = "gpt-5"  # or "gpt-3.5-turbo" for faster, less expensive responses