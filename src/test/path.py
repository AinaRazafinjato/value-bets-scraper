# Add project path to import the scraper
import os
from pathlib import Path

# Get the path to the data directory
icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "vbicon.ico")

if not os.path.exists(icon_path):
    print("Data directory does not exist.")
else:
    print(icon_path)
