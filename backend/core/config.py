import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings and environment variables."""
    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
    IONOS_API_TOKEN: str | None = os.getenv("IONOS_API_TOKEN")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    IONOS_URL: str | None = os.getenv("IONOS_URL")
    MODEL_ID: str | None = os.getenv("MODEL_ID")
    SIGHTENGINE_USER: str | None = os.getenv("SIGHTENGINE_USER")
    SIGHTENGINE_API: str | None = os.getenv("SIGHTENGINE_API")

# Instantiate a global settings object to be imported across the app
settings = Settings()