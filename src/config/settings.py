"""
Application Configuration Module

This module contains settings and configuration parameters for the ValueBets scraper.
It provides centralized access to application settings such as authentication credentials,
request timeouts, and other configurable parameters.
"""

# Authentication settings
AUTH_CREDENTIALS = {
    "username": "",  # Fill in your oddportal username
    "password": "",  # Fill in your oddportal password
}

# Request settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Scraping settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
BASE_URL = "https://oddportal.com"  # Replace with actual URL if different

# Output settings
DATA_DIRECTORY = "data"
LOG_LEVEL = "INFO"