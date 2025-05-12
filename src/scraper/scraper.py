from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
import time
from loguru import logger
from typing import Tuple, Optional, Callable
import os
from plyer import notification
import getpass
import platform
import ctypes
import random


def configure_logger() -> None:
    """Set up logging configuration and ensure logs directory exists."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logger.add(
        os.path.join(logs_dir, "scraper.log"),
        rotation="1 MB",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
    )
    logger.info("Logger configured successfully")


def setup_browser() -> Tuple[Playwright, Browser, Page]:
    """Set up and return a Playwright browser and page context."""
    logger.info("Launching Playwright in headless mode...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    context.set_default_navigation_timeout(60000)
    page = context.new_page()
    logger.info("Browser and page context created successfully")
    return playwright, browser, page


def navigate_to_value_bets(page: Page, attempt: int = 1, max_attempts: int = 3) -> Optional[str]:
    """Navigate to the value bets page and retrieve its HTML content with retry mechanism."""
    try:
        logger.info(f"Attempt {attempt}/{max_attempts}: Navigating to Value Bets section...")
        
        # Random delay between attempts to avoid being detected as a bot
        if attempt > 1:
            delay = random.uniform(3, 7)
            logger.info(f"Adding random delay of {delay:.2f} seconds before retry")
            time.sleep(delay)
        
        page.goto("https://www.oddsportal.com/value-bets/")
        logger.info("Page loaded successfully")
        
        # Random pause to simulate human behavior
        time.sleep(random.uniform(1, 3))
        
        logger.info("Selecting 'All sports' filter...")
        page.get_by_role("listitem").filter(has_text="All sports").click()
        
        # Another small random delay
        time.sleep(random.uniform(2, 4))
        
        html_content = page.content()
        
        # Basic validation to ensure we got meaningful content
        if "value-bets" in html_content.lower() and len(html_content) > 5000:
            logger.info("HTML content retrieved successfully")
            return html_content
        else:
            logger.warning("Retrieved HTML doesn't appear to contain value bets data")
            if attempt < max_attempts:
                logger.info(f"Retrying (attempt {attempt+1}/{max_attempts})...")
                return navigate_to_value_bets(page, attempt + 1, max_attempts)
            return None
            
    except Exception as e:
        logger.error(f"Error during page navigation or interaction: {e}")
        if attempt < max_attempts:
            logger.info(f"Retrying (attempt {attempt+1}/{max_attempts})...")
            return navigate_to_value_bets(page, attempt + 1, max_attempts)
        return None


def extract_data_from_html(html: str) -> pd.DataFrame:
    """Extract value bets data from HTML content."""
    logger.info("Parsing HTML content with BeautifulSoup")
    soup = BeautifulSoup(html, "html.parser")
    valuebets = soup.select("div.tabs div.visible")

    data = {
        "sports": [],
        "countries": [],
        "leagues": [],
        "pronos": [],
        "date": [],
        "time": [],
        "team_1": [],
        "team_2": [],
        "outcome": [],
        "bookmaker": [],
        "odds": [],
        "value": [],
        "probability": [],
    }

    for valuebet in valuebets:
        extract_header_data(valuebet, data)
        extract_match_data(valuebet, data)
        extract_bookmaker_data(valuebet, data)

    if not data["sports"]:
        logger.error("No data extracted from the HTML content")
        raise ValueError("No data extracted from HTML.")

    logger.info("Data extraction completed successfully")
    return pd.DataFrame(data)


def extract_header_data(valuebet, data):
    """Extract header data from a value bet."""
    header = valuebet.select("a")
    data["sports"].append(header[0].text.strip() if len(header) > 0 else None)
    data["countries"].append(header[1].text.strip() if len(header) > 1 else None)
    data["leagues"].append(
        " ".join(header[2].text.split()) if len(header) > 2 else None
    )


def extract_match_data(valuebet, data):
    """Extract match data from a value bet."""
    match_info = valuebet.find_all("div", class_="flex min-h-[90px] w-full")
    for match in match_info:
        p_elements = match.select("p")
        match_data = [p.text.strip() for p in p_elements]
        if len(match_data) >= 9:
            data["pronos"].append(match_data[0])
            data["date"].append(match_data[1])
            data["time"].append(match_data[2])
            data["team_1"].append(match_data[3])
            data["team_2"].append(match_data[4])
            data["outcome"].append(match_data[5])
            data["odds"].append(match_data[6])
            data["value"].append(match_data[7])
            data["probability"].append(match_data[8])


def extract_bookmaker_data(valuebet, data):
    """Extract bookmaker data from a value bet."""
    bookmaker_info = valuebet.find_all("div", class_="h-[25px] w-[75px]")
    for bookmaker in bookmaker_info:
        img = bookmaker.find("img")
        data["bookmaker"].append(img["alt"] if img and "alt" in img.attrs else None)


def clean_and_process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and process the extracted data."""
    logger.info("Cleaning and processing the extracted data")
    today = datetime.now()

    df["probability"] = pd.to_numeric(
        df["probability"].str.replace("%", "", regex=False), errors="coerce"
    )
    df["date"] = (
        df["date"]
        .str.replace(",", "")
        .replace(
            {
                "Today": today.strftime("%d %b"),
                "Tomorr.": (today + timedelta(days=1)).strftime("%d %b"),
            }
        )
    )
    df["date"] = pd.to_datetime(
        df["date"] + f" {today.year}", format="%d %b %Y", errors="coerce"
    )
    df["time"] = pd.to_datetime(
        df["time"], format="%H:%M", errors="coerce"
    ).dt.strftime("%H:%M")
    df[["value", "odds"]] = df[["value", "odds"]].apply(pd.to_numeric, errors="coerce")
    df.sort_values(
        by=["probability", "date", "time"], ascending=[False, True, True], inplace=True
    )

    logger.info("Data cleaning and processing completed successfully")
    return df


def export_data_to_csv(df: pd.DataFrame, file_name: str) -> None:
    """Export the cleaned data to a CSV file."""
    logger.info("Exporting data to CSV")
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, file_name)
    df.to_csv(csv_path, index=False)
    logger.info(f"Data exported successfully.")


def send_notification(high_probability_count: int) -> None:
    """Send a system notification about value bets."""
    try:
        # Define the path to an icon file
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "vbicon.ico")
        
        # Ensure the icon directory exists
        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
        
        # On Windows, set the AppID for proper notification branding
        if platform.system() == "Windows":
            try:
                app_id = "ValueBetsScanner.Notification.1"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            except Exception as e:
                logger.error(f"Failed to set AppID: {e}")
        
        # Display singular form if there's only one value bet
        bet_message = "value bet found!" if high_probability_count == 1 else "value bets found!"
        
        notification.notify(
            title="ValueBets Alert",
            message=f"🔔 {high_probability_count} {bet_message}",
            app_icon=icon_path if os.path.exists(icon_path) else None,
            timeout=30
        )
        logger.info(f"Notification sent for {high_probability_count} high probability value bets")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def scrape_with_retries(max_attempts: int = 3, callback: Optional[Callable] = None) -> Optional[pd.DataFrame]:
    """Execute the scraping process with multiple retries."""
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Starting scraping attempt {attempt}/{max_attempts}")
        if callback:
            callback(1, 5, f"Tentative de scraping {attempt}/{max_attempts}...")
        
        playwright, browser, page = None, None, None
        
        try:
            if callback:
                callback(2, 5, "Initialisation du navigateur...")
            
            playwright, browser, page = setup_browser()
            
            if callback:
                callback(3, 5, "Navigation vers OddsPortal...")
            
            html = navigate_to_value_bets(page)
            
            if html:
                if callback:
                    callback(4, 5, "Extraction des données...")
                
                df = extract_data_from_html(html)
                
                if not df.empty:
                    if callback:
                        callback(5, 5, "Traitement des données...")
                    
                    return clean_and_process_data(df)
            
            logger.warning(f"Attempt {attempt} failed to retrieve valid data")
            
            # Wait before next attempt
            if attempt < max_attempts:
                wait_time = random.uniform(5, 15)
                
                if callback:
                    callback(attempt, max_attempts, f"Échec de la tentative {attempt}. Nouvelle tentative dans {wait_time:.0f}s...")
                
                logger.info(f"Waiting {wait_time:.2f} seconds before next attempt")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Error in scraping attempt {attempt}: {e}")
            
            if callback:
                callback(attempt, max_attempts, f"Erreur: {str(e)}")
        finally:
            if browser:
                browser.close()
                logger.info("Browser closed")
            if playwright:
                playwright.stop()
                logger.info("Playwright stopped")
    
    logger.error("All scraping attempts failed")
    
    if callback:
        callback(max_attempts, max_attempts, "Toutes les tentatives de scraping ont échoué.")
    
    return None


def main(callback: Optional[Callable] = None) -> Optional[pd.DataFrame]:
    """Main function to execute the scraping process with retries.
    
    Args:
        callback: Optional callback function that takes 3 parameters:
                 - step: current step number
                 - total_steps: total number of steps
                 - message: progress message
                 
    Returns:
        Optional[pd.DataFrame]: The scraped data or None if scraping failed
    """
    if callback:
        callback(1, 5, "Configuration des journaux...")
    
    configure_logger()
    logger.info("Starting the value bets scraping process")
    
    if callback:
        callback(2, 5, "Lancement du scraping...")
    
    df = scrape_with_retries(max_attempts=3, callback=callback)
    
    if df is not None and not df.empty:
        if callback:
            callback(3, 5, "Données récupérées, analyse en cours...")
            
        # Check for values > 50 in the 'probability' column
        high_probability_count = (df["probability"] > 50).sum()
        
        if high_probability_count > 0:
            send_notification(high_probability_count)
        
        if callback:
            callback(4, 5, "Sauvegarde des données...")
            
        export_data_to_csv(df, "data.csv")
        
        if callback:
            callback(5, 5, f"Opération terminée avec succès! {len(df)} value bets trouvées.")
            
        logger.info("Scraping process completed successfully")
        return df
    else:
        if callback:
            callback(5, 5, "Échec de la récupération des données après plusieurs tentatives")
            
        logger.error("Failed to retrieve value bets data after all attempts")
        return None


if __name__ == "__main__":
    main()