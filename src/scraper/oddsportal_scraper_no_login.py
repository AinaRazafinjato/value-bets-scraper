from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
import time
from loguru import logger
from typing import Tuple, Optional
import os


def configure_logger() -> None:
    """Set up logging configuration and ensure logs directory exists."""
    logs_dir = os.path.join(os.path.dirname(__file__), "../logs")
    os.makedirs(logs_dir, exist_ok=True)
    logger.add(
        os.path.join(logs_dir, "oddsportal_scraper_no_login.log"),
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
    browser = playwright.chromium.launch(headless=True)  # Changed to headless=True
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    )
    context.set_default_navigation_timeout(60000)
    page = context.new_page()
    logger.info("Browser and page context created successfully")
    return playwright, browser, page


def navigate_to_value_bets(page: Page) -> Optional[str]:
    """Navigate to the value bets page and retrieve its HTML content."""
    try:
        logger.info("Navigating to Value Bets section...")
        page.goto("https://www.oddsportal.com/value-bets/")
        logger.info("Page loaded successfully")
        logger.info("Selecting 'All sports' filter...")
        page.get_by_role("listitem").filter(has_text="All sports").click()
        time.sleep(2)
        html_content = page.content()
        logger.info("HTML content retrieved successfully")
        return html_content
    except Exception as e:
        logger.error(f"Error during page navigation or interaction: {e}")
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
    data_dir = os.path.join(os.path.dirname(__file__), "../data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, file_name)
    df.to_csv(csv_path, index=False)
    logger.info(f"Data exported successfully")


def main() -> None:
    """Main function to execute the scraping process."""
    configure_logger()
    logger.info("Starting the scraping process")
    playwright, browser, page = None, None, None
    try:
        playwright, browser, page = setup_browser()
        html = navigate_to_value_bets(page)
        if html:
            df = extract_data_from_html(html)
            df = clean_and_process_data(df)
            export_data_to_csv(df, "oddsportal_data_no_login.csv")
        else:
            logger.warning("No HTML content to parse.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if browser:
            browser.close()
            logger.info("Browser closed")
        if playwright:
            playwright.stop()
            logger.info("Playwright stopped")


if __name__ == "__main__":
    main()
