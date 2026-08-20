import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- Bridge Identity ---
    app_name: str = "ARIA Bridge"
    app_version: str = "1.0.0"
    
    # --- Auth ---
    # Key that external clients (Vitruvius/ChatGPT) must provide to call the Bridge
    aria_bridge_api_key: str = os.getenv("ARIA_BRIDGE_API_KEY", "aria-bridge-v1-9823472394")
    
    # --- ARIAEngine Connection ---
    # The production ARIAEngine URL
    ariaengine_url: str = os.getenv("ARIAENGINE_URL", "https://ariaengine-production.up.railway.app")
    # The API key required by ARIAEngine's client protocol
    aria_client_api_key: str = os.getenv("ARIA_CLIENT_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
