from dotenv import load_dotenv
import os

def load_settings() -> None:
    """Load environment variables from .env file."""
    load_dotenv()

# Exemple d'utilisation pour récupérer une variable (si nécessaire)
# USER_AGENT = os.getenv("USER_AGENT")