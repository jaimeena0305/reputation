import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    BASE_DIR: Path = BASE_DIR
    
    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # AI Providers
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "heuristic").lower()
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-1.5-flash")
    
    # External review APIs
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    YELP_API_KEY: str = os.getenv("YELP_API_KEY", "").strip()
    
    # Resend email delivery
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "").strip()
    REPORT_SENDER_EMAIL: str = os.getenv("REPORT_SENDER_EMAIL", "reputation@agency.local")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'reputation_agent.db'}")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "").strip()

settings = Settings()
