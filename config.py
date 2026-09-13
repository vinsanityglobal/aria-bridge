import os
from pydantic_settings import BaseSettings


def _env(name: str, default: str = "") -> str:
    """Read a deployment secret/config value without accepting copied whitespace."""
    return os.getenv(name, default).strip()


class Settings(BaseSettings):
    # --- Bridge Identity ---
    app_name: str = "ARIA Bridge"
    app_version: str = "1.1.0"

    # --- Auth ---
    # Shared Bridge key for general Bridge clients. No hard-coded fallback is permitted.
    aria_bridge_api_key: str = _env("ARIA_BRIDGE_API_KEY")

    # Dedicated AESS credential for governed CR-028 recall.
    # Caller identity is derived from possession of this credential and is not trusted
    # from request-body metadata.
    aess_bridge_api_key: str = _env("AESS_BRIDGE_API_KEY")
    aess_caller_id: str = _env("AESS_CALLER_ID", "aess-spatial-awareness")

    # --- ARIAEngine Connection ---
    # The production ARIAEngine URL
    ariaengine_url: str = _env("ARIAENGINE_URL", "https://ariaengine-production.up.railway.app")
    # The API key required by ARIAEngine's client protocol
    aria_client_api_key: str = _env("ARIA_CLIENT_API_KEY")

    # Existing ARIA capability name that should service bounded interpretation.
    # Intentionally has no default: Bridge must not invent Kernel capabilities.
    aria_interpret_capability: str | None = os.getenv("ARIA_INTERPRET_CAPABILITY")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
