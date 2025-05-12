import customtkinter as ctk
import pandas as pd
import threading
import time
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pathlib import Path
from datetime import datetime
import numpy as np
from loguru import logger

# Add project path to import the scraper
sys.path.append(str(Path(__file__).parent.parent.parent))

# Define paths
ASSETS_DIR = os.path.join(Path(__file__).parent.parent.parent, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "vbicon.ico")
LOGS_DIR = os.path.join(Path(__file__).parent.parent.parent, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuration de loguru au lieu de logging
log_file = os.path.join(LOGS_DIR, f"vbscraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Supprimer les handlers par défaut de loguru
logger.remove()

# Ajouter des handlers personnalisés pour le fichier et la console
logger.add(
    log_file,
    rotation="1 MB", 
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}", 
    backtrace=True, 
    diagnose=True
)
logger.add(
    sys.stderr, 
    level="INFO", 
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)

# Ajouter cette fonction pour simplifier les chemins dans les logs
def format_path(path):
    """Convertit les chemins absolus en chemins relatifs pour les logs."""
    project_root = str(Path(__file__).parent.parent.parent)
    return path.replace(project_root, ".")


# Color and font definitions
COLORS = {
    "card_bg": ("#FFFFFF", "#1E293B"),
    "header_bg": ("#F0F9FF", "#2D3748"),
    "accent": ("#2563EB", "#60A5FA"),
    "accent_hover": ("#1D4ED8", "#3B82F6"),
    "success_bg": ("#ECFDF5", "#064E3B"),
    "success_text": ("#059669", "#22C55E"),
    "warning_bg": ("#FFFBEB", "#713F12"),
    "warning_text": ("#B45309", "#EAB308"),
    "error_bg": ("#FEF2F2", "#7F1D1D"),
    "error_text": ("#B91C1C", "#EF4444"),
    "text_primary": ("#111827", "#F1F5F9"),
    "text_secondary": ("#4B5563", "#94A3B8"),
    "border": ("#E5E7EB", "#334155"),
    "gradient_start": ("#2563EB", "#2563EB"),
    "gradient_end": ("#1D4ED8", "#1D4ED8"),
}

FONTS = {
    "header": ("Inter", 12, "bold"),
    "date": ("Inter", 11),
    "teams": ("Inter", 13, "bold"),
    "prono": ("Inter", 11),
    "outcome": ("Inter", 11, "bold"),
    "bookmaker": ("Inter", 11),
    "odds": ("Inter", 12, "bold"),
    "value": ("Inter", 11),
    "prob": ("Inter", 12, "bold"),
    "title": ("Inter", 18, "bold"),
    "subtitle": ("Inter", 14),
    "error": ("Inter", 12, "bold"),
    "button": ("Inter", 12, "bold"),
    "small": ("Inter", 10),
}

# Import the scraper module
try:
    # Assurez-vous que le répertoire racine du projet est dans sys.path
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    
    # Importation directe depuis le module src.scraper
    from src.scraper.scraper import main as run_scraper
    
    # Vérifiez que l'importation a bien fonctionné
    logger.info(f"Scraper module successfully imported from {format_path(str(project_root))}")
    
    # Vérifiez aussi que le répertoire data existe
    data_dir = os.path.join(project_root, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Created data directory at {format_path(data_dir)}")
    else:
        logger.info(f"Data directory found at {format_path(data_dir)}")
        
    SCRAPER_AVAILABLE = True
except ImportError as e:
    SCRAPER_AVAILABLE = False
    logger.error(f"Failed to import scraper module: {str(e)}")
    logger.warning("Scraping module not available. Running in simulation mode.")
    logger.critical(f"Uncaught exception in main thread: {str(e)}", exc_info=True)


class ValueBetScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Basic configuration
        self.title("Value Bets Scraper")
        self.geometry("1280x800")
        logger.info("Initializing ValueBetScraperApp")
        
        # Set application icon for both window and taskbar
        self.set_app_icon()
        
    def set_app_icon(self):
        """Set application icon for both window and taskbar across platforms"""
        if os.path.exists(ICON_PATH):
            # Set window icon with the standard method
            self.iconbitmap(ICON_PATH)
            
            # Special handling for Windows taskbar icon
            if sys.platform.startswith('win'):
                try:
                    import ctypes
                    myappid = f'vbscraper.app.v1.0'  # Arbitrary string
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                    logger.info("Windows taskbar icon set successfully")
                except Exception as e:
                    logger.warning(f"Could not set Windows taskbar icon: {e}")
            
            # For macOS (although CustomTkinter doesn't fully support this)
            elif sys.platform == 'darwin':
                try:
                    # macOS uses .icns format, might need conversion
                    logger.info("On macOS, icon setting is handled differently")
                except Exception as e:
                    logger.warning(f"Could not set macOS icon: {e}")

            
        # Path to data file
        self.data_path = os.path.join(Path(__file__).parent.parent.parent, "data", "data.csv")
        
        # Apply theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Data variables
        self.data = None
        self.filtered_data = None
        self.scraping_thread = None
        self.current_page = 1
        self.items_per_page = 5
        self.pagination_controls = None
        self.filter_controls = {}

        # Loading animation frames
        self.loading_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.animation_running = False
        
        # Set up UI components
        self._setup_sidebar()
        self._setup_main_area()
        
    def _setup_sidebar(self):
        """Set up the sidebar with navigation buttons"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)
        
        # Navigation section title
        self.nav_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="NAVIGATION",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS["text_secondary"][mode_index],
        )
        self.nav_title.grid(row=1, column=0, padx=25, pady=(5, 10), sticky="w")
        
        # Scrape button
        self.scrape_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Scrape Data",
            command=self.start_scraping,
            font=FONTS["button"],
            height=45,
            corner_radius=8,
            fg_color=COLORS["accent"][mode_index],
            hover_color=COLORS["accent_hover"][mode_index],
        )
        self.scrape_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Display bets button
        self.display_cards_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Display Bets",
            command=self.display_data_cards,
            font=FONTS["button"],
            height=45,
            corner_radius=8,
        )
        self.display_cards_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # Stats button
        self.stats_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Statistics",
            command=self.show_statistics,
            font=FONTS["button"],
            height=45,
            corner_radius=8,
        )
        self.stats_button.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        # Settings section title
        self.settings_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="SETTINGS",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS["text_secondary"][mode_index],
        )
        self.settings_title.grid(row=5, column=0, padx=25, pady=(20, 10), sticky="w")
        
        # Theme selector
        theme_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        theme_frame.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        self.theme_option = ctk.CTkOptionMenu(
            theme_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode,
            font=ctk.CTkFont(family="Inter", size=12),
            width=160,
        )
        self.theme_option.pack(side="right")
        self.theme_option.set(ctk.get_appearance_mode().capitalize())
        
        # Version info
        version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Version 1.0",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"][mode_index]
        )
        version_label.grid(row=9, column=0, pady=(10, 20))
        
    def _setup_main_area(self):
        """Set up the main content area"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header bar
        self.header_bar = ctk.CTkFrame(self.main_frame, height=60, fg_color="transparent")
        self.header_bar.grid(row=0, column=0, sticky="ew", pady=(10, 5))
        
        self.title_label = ctk.CTkLabel(
            self.header_bar, 
            text="Dashboard", 
            font=FONTS["title"]
        )
        self.title_label.pack(side="left", padx=10)
        
        # Content area
        self.content_frame = ctk.CTkFrame(
            self.main_frame, 
            fg_color=COLORS["card_bg"][mode_index],
            border_width=1,
            border_color=COLORS["border"][mode_index],
            corner_radius=12
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Welcome content
        welcome_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        welcome_container.pack(expand=True)
        
        welcome_title = ctk.CTkLabel(
            welcome_container,
            text="Welcome to Value Bets Scraper",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=COLORS["accent"][mode_index]
        )
        welcome_title.pack(pady=(0, 20))
        
        welcome_description = ctk.CTkLabel(
            welcome_container,
            text="Find the best odds and value betting opportunities",
            font=ctk.CTkFont(family="Inter", size=16),
            text_color=COLORS["text_secondary"][mode_index]
        )
        welcome_description.pack(pady=(0, 30))
        
        # Start button
        start_button = ctk.CTkButton(
            welcome_container,
            text="Start Scraping",
            command=self.start_scraping,
            font=FONTS["button"],
            height=50,
            width=220,
            corner_radius=25,
            fg_color=COLORS["accent"][mode_index],
            hover_color=COLORS["accent_hover"][mode_index],
        )
        start_button.pack(pady=10)
        
        # Progress elements (hidden by default)
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, 
            width=600,
            height=15,
            corner_radius=7
        )
        self.progress_spinner_label = ctk.CTkLabel(
            self.progress_frame,
            text="⠋",
            font=ctk.CTkFont(size=24),
            text_color=COLORS["accent"][mode_index]
        )
        self.progress_status = ctk.CTkLabel(
            self.progress_frame, 
            text="",
            font=ctk.CTkFont(family="Inter", size=14)
        )
        
        # Notification area
        self.notification_frame = ctk.CTkFrame(
            self.main_frame, 
            height=50, 
            fg_color="transparent"
        )
        self.notification_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.notification_label = ctk.CTkLabel(
            self.notification_frame, 
            text="",
            font=ctk.CTkFont(family="Inter", size=14)
        )
        self.notification_label.pack(pady=10)

    def change_appearance_mode(self, new_appearance_mode):
        """Change the app's appearance mode"""
        ctk.set_appearance_mode(new_appearance_mode.lower())
        self._update_ui_colors()

    def _update_ui_colors(self):
        """Update UI colors after appearance mode change"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        self.nav_title.configure(text_color=COLORS["text_secondary"][mode_index])
        self.settings_title.configure(text_color=COLORS["text_secondary"][mode_index])
        
        self.content_frame.configure(
            fg_color=COLORS["card_bg"][mode_index],
            border_color=COLORS["border"][mode_index]
        )
        
        if self.data is not None:
            self.display_data_cards()
    
    def start_scraping(self):
        """Start the scraping process in a separate thread"""
        logger.info("Starting scraping process")
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        # Set up UI for scraping
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        self.progress_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(100, 20))
        
        # Setup spinner animation
        self.progress_spinner_label.configure(text_color=COLORS["accent"][mode_index])
        self.progress_spinner_label.pack(pady=(0, 15))
        self.animation_running = True
        self.animate_spinner()
        
        self.progress_status.configure(text="Initializing scraper...")
        self.progress_status.pack(pady=(0, 100))
        
        # Disable buttons during scraping
        self.scrape_button.configure(state="disabled")
        self.display_cards_button.configure(state="disabled")
        self.stats_button.configure(state="disabled")
        
        # Start scraping in a separate thread
        self.scraping_thread = threading.Thread(target=self._scraping_task)
        self.scraping_thread.daemon = True
        self.scraping_thread.start()
    
    def animate_spinner(self):
        """Animate the loading spinner"""
        if not self.animation_running:
            return
            
        self.current_frame = (self.current_frame + 1) % len(self.loading_frames)
        self.progress_spinner_label.configure(text=self.loading_frames[self.current_frame])
        self.after(100, self.animate_spinner)
    
    def _scraping_task(self):
        """Execute the scraping process"""
        logger.info(f"Executing scraping task, SCRAPER_AVAILABLE={SCRAPER_AVAILABLE}")
        
        # Vérification des chemins importants
        logger.info(f"Data path: {format_path(self.data_path)}")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        if SCRAPER_AVAILABLE:
            logger.info("Using real scraper")
            self._real_scraping()
        else:
            logger.warning("Scraper not available, running simulation")
            self.simulate_scraping()
    
    def simulate_scraping(self):
        """Simulate the scraping process for testing UI"""
        logger.info("Running scraping simulation")
        steps = 10
        for i in range(steps + 1):
            progress = i / steps
            message = f"Simulation step {i}/{steps}"
            self.update_progress(progress, message)
            time.sleep(0.5)
        
        # Create sample data
        self.data = pd.DataFrame({
            "sports": ["Football"] * 10,
            "countries": ["France", "England", "Spain", "Italy", "Germany", "France", "England", "Spain", "Italy", "Germany"],
            "leagues": ["Ligue 1", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 2", "Championship", "Segunda", "Serie B", "2. Bundesliga"],
            "team_1": ["PSG", "Man City", "Barcelona", "Inter", "Bayern", "Monaco", "Liverpool", "Atletico", "Juventus", "Leipzig"],
            "team_2": ["Lyon", "Arsenal", "Real Madrid", "Milan", "Dortmund", "Marseille", "Chelsea", "Sevilla", "Roma", "Wolfsburg"],
            "date": ["2023-05-01", "2023-05-02", "2023-05-03", "2023-05-04", "2023-05-05", "2023-05-06", "2023-05-07", "2023-05-08", "2023-05-09", "2023-05-10"],
            "time": ["20:00", "18:45", "21:00", "19:30", "20:15", "21:30", "17:00", "22:00", "18:00", "19:00"],
            "pronos": ["1", "X", "2", "Over 2.5", "BTTS", "1X", "X2", "Under 2.5", "No BTTS", "1 & Over 1.5"],
            "outcome": ["Home", "Draw", "Away", "Over", "Yes", "Home/Draw", "Draw/Away", "Under", "No", "Home"],
            "bookmaker": ["Bet365", "Unibet", "1xBet", "Bwin", "Betway", "William Hill", "Betclic", "Winamax", "PaddyPower", "Betfair"],
            "odds": [2.1, 3.5, 2.8, 1.95, 1.8, 1.6, 2.2, 2.5, 2.0, 3.2],
            "value": [8.0, 12.0, 7.0, 5.0, 9.0, 6.5, 11.0, 8.5, 7.5, 10.0],
            "probability": [52.3, 31.2, 38.7, 56.2, 61.8, 68.5, 49.2, 43.5, 54.3, 35.8]
        })
        
        self.filtered_data = self.data.copy()
        self.show_notification("Simulation completed. Data generated.", "success")
        
        # Re-enable buttons and clean up
        self.after(1000, lambda: self.scrape_button.configure(state="normal"))
        self.after(1000, lambda: self.display_cards_button.configure(state="normal"))
        self.after(1000, lambda: self.stats_button.configure(state="normal"))
        self.animation_running = False
        self.after(1000, self._cleanup_after_scraping)
        self.after(1500, self.display_data_cards)
    
    def _real_scraping(self):
        """Execute actual scraping with the main function from scraper"""
        try:
            def progress_callback(step, total_steps, message):
                progress = step / total_steps if total_steps > 0 else 0
                self.update_progress(progress, message)
            
            df = run_scraper(callback=progress_callback)
            
            if df is not None and not df.empty:
                self.data = df
                self.filtered_data = df.copy()
                bet_count = len(df)
                self.show_notification(f"Scraping completed successfully! {bet_count} value bets found.", "success")
                self.after(1500, self.display_data_cards)
            else:
                self.show_notification("Scraping completed but no data was retrieved.", "warning")
            
        except Exception as e:
            self.show_notification(f"Error during execution: {str(e)}", "error")
            logger.exception(f"Error during scraping: {str(e)}")  # logger.exception au lieu de logger.error avec exc_info
        finally:
            self.after(1000, lambda: self.scrape_button.configure(state="normal"))
            self.after(1000, lambda: self.display_cards_button.configure(state="normal"))
            self.after(1000, lambda: self.stats_button.configure(state="normal"))
            self.animation_running = False
            self.after(1000, self._cleanup_after_scraping)
    
    def create_match_card(self, parent, league, prono, date, time, teams, outcome, bookmaker, odds, value, prob):
        """Create an improved match card with better styling"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        card = ctk.CTkFrame(
            parent, 
            corner_radius=10, 
            fg_color=COLORS["card_bg"][mode_index], 
            border_width=1,
            border_color=COLORS["border"][mode_index]
        )
        card.pack(fill="x", padx=10, pady=6, anchor="n")
        
        # Header with league and date
        header = ctk.CTkFrame(
            card, 
            fg_color=COLORS["header_bg"][mode_index], 
            corner_radius=8, 
            height=30
        )
        header.pack(fill="x", padx=8, pady=(8, 0))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, 
            text=league, 
            font=FONTS["header"],
            text_color=COLORS["text_primary"][mode_index]
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            header, 
            text=f"{date} • {time}", 
            font=FONTS["date"],
            text_color=COLORS["text_primary"][mode_index]
        ).pack(side="right", padx=10)
        
        # Teams and match info
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=(8, 0))
        
        teams_frame = ctk.CTkFrame(content, fg_color="transparent")
        teams_frame.pack(fill="x", anchor="w")
        
        ctk.CTkLabel(
            teams_frame, 
            text=teams, 
            font=FONTS["teams"],
            text_color=COLORS["text_primary"][mode_index]
        ).pack(side="left")
        
        prono_frame = ctk.CTkFrame(content, fg_color="transparent")
        prono_frame.pack(fill="x", pady=(4, 0))
        
        ctk.CTkLabel(
            prono_frame, 
            text=f"Prediction: {prono}", 
            font=FONTS["prono"], 
            text_color=COLORS["text_secondary"][mode_index]
        ).pack(side="left")
        
        # Bet details in a horizontal layout
        bet_info = ctk.CTkFrame(card, fg_color="transparent")
        bet_info.pack(fill="x", padx=12, pady=(6, 10))
        
        # Left side - Outcome and bookmaker
        left_info = ctk.CTkFrame(bet_info, fg_color="transparent")
        left_info.pack(side="left")
        
        # Styled outcome label
        outcome_label = ctk.CTkLabel(
            left_info, 
            text=outcome, 
            width=70,
            font=FONTS["outcome"],
            fg_color=COLORS["accent"][mode_index], 
            corner_radius=6,
            text_color=("white", "white")
        )
        outcome_label.pack(side="left", pady=2)
        
        ctk.CTkLabel(
            left_info, 
            text=bookmaker, 
            width=100, 
            font=FONTS["bookmaker"],
            text_color=COLORS["text_primary"][mode_index]
        ).pack(side="left", padx=(10, 0))
        
        # Center - Odds and value
        center_info = ctk.CTkFrame(bet_info, fg_color="transparent")
        center_info.pack(side="left", padx=15)
        
        ctk.CTkLabel(
            center_info, 
            text=f"@{odds}", 
            font=FONTS["odds"],
            text_color=COLORS["text_primary"][mode_index]
        ).pack(side="left")
        
        # Handle value display
        try:
            if isinstance(value, str) and "%" in value:
                value_float = float(value.strip('%'))
                value_display = value
            else:
                value_float = float(value)
                value_display = f"{value_float}"
                
            value_color = COLORS["success_text"][mode_index] if value_float > 7 else COLORS["text_secondary"][mode_index]
        except (ValueError, AttributeError):
            value_color = COLORS["text_secondary"][mode_index]
            value_display = str(value) if value is not None else "0"
        
        ctk.CTkLabel(
            center_info, 
            text=f"Value: {value_display}", 
            font=FONTS["value"],
            text_color=value_color
        ).pack(side="left", padx=(15, 0))
        
        # Right - Probability
        ctk.CTkLabel(
            bet_info, 
            text=f"{prob}", 
            width=70, 
            font=FONTS["prob"], 
            fg_color=COLORS["success_bg"][mode_index], 
            text_color=COLORS["success_text"][mode_index],
            corner_radius=6
        ).pack(side="right")
    
    def create_pagination_controls(self, parent, total_items, items_per_page, on_page_change):
        """Create pagination controls"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        control_frame = ctk.CTkFrame(parent, fg_color="transparent")
        control_frame.pack(fill="x", pady=10)
        
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        # Items info
        items_info = ctk.CTkLabel(
            control_frame, 
            text=f"Total: {total_items} bets",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS["text_primary"][mode_index]
        )
        items_info.pack(side="right", padx=15)
        
        # Navigation controls
        nav_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        nav_frame.pack(side="left", padx=15)
        
        # Previous page button
        prev_btn = ctk.CTkButton(
            nav_frame, 
            text="←",
            width=35,
            height=35, 
            corner_radius=17,
            command=lambda: on_page_change("prev"),
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"][mode_index],
            hover_color=COLORS["accent_hover"][mode_index],
        )
        prev_btn.pack(side="left", padx=5)
        
        # Page indicator
        page_label = ctk.CTkLabel(
            nav_frame, 
            text=f"Page 1/{total_pages}",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS["text_primary"][mode_index]
        )
        page_label.pack(side="left", padx=15)
        
        # Next page button
        next_btn = ctk.CTkButton(
            nav_frame, 
            text="→", 
            width=35,
            height=35,
            corner_radius=17,
            command=lambda: on_page_change("next"),
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"][mode_index],
            hover_color=COLORS["accent_hover"][mode_index],
        )
        next_btn.pack(side="left", padx=5)
        
        # Items per page selector
        per_page_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        per_page_frame.pack(side="left", padx=30)
        
        per_page_label = ctk.CTkLabel(
            per_page_frame,
            text="Bets per page:",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS["text_primary"][mode_index]
        )
        per_page_label.pack(side="left", padx=(0, 10))
        
        def change_per_page(value):
            self.items_per_page = int(value)
            on_page_change("refresh")
            
        per_page_selector = ctk.CTkOptionMenu(
            per_page_frame,
            values=["3", "5", "10", "20"],
            command=change_per_page,
            width=60,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        per_page_selector.pack(side="left")
        per_page_selector.set(str(items_per_page))
        
        return {
            "prev_btn": prev_btn,
            "next_btn": next_btn,
            "page_label": page_label,
            "total_pages": total_pages,
            "per_page_selector": per_page_selector
        }

    def update_matches_display(self, page, matches, scroll_frame):
        """Update the display of matches for the specified page"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        # Clear existing widgets
        for widget in scroll_frame.winfo_children():
            widget.destroy()
        
        # Calculate start and end indices for this page
        start_idx = (page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(matches))
        
        if len(matches) == 0:
            # Show empty state
            empty_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            empty_frame.pack(expand=True, fill="both", pady=50)
            
            empty_message = ctk.CTkLabel(
                empty_frame,
                text="No bets available",
                font=ctk.CTkFont(family="Inter", size=16),
                text_color=COLORS["text_secondary"][mode_index]
            )
            empty_message.pack(pady=20)
            
            retry_button = ctk.CTkButton(
                empty_frame,
                text="Start Scraping",
                command=self.start_scraping,
                font=FONTS["button"],
                height=40,
                width=180,
                fg_color=COLORS["accent"][mode_index],
                hover_color=COLORS["accent_hover"][mode_index],
            )
            retry_button.pack()
            return
        
        # Display matches for current page
        for i in range(start_idx, end_idx):
            self.create_match_card(scroll_frame, **matches[i])

    def format_date_for_display(self, date_str):
        """Convert date to user-friendly format"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()
            match_date = date_obj.date()
            
            delta = (match_date - today).days
            
            if delta == 0:
                return "Today"
            elif delta == 1:
                return "Tomorrow"
            else:
                return date_obj.strftime('%d/%m')
        
        except Exception:
            return date_str

    def prepare_data_for_cards(self):
        """Prepare data for card display"""
        if self.filtered_data is None or self.filtered_data.empty:
            return []
        
        formatted_data = []
        for _, row in self.filtered_data.iterrows():
            # Format date
            display_date = self.format_date_for_display(str(row["date"]))
            
            # Format data for display
            teams = f"{row['team_1']} - {row['team_2']}"
            league = f"{row['sports']} / {row['countries']} / {row['leagues']}"
            prob = f"{float(row['probability']):.1f}%"
            
            # Format value correctly
            if isinstance(row['value'], str) and '%' in row['value']:
                value = row['value']
            else:
                try:
                    value = float(row['value'])
                except (ValueError, TypeError):
                    value = 0.0
            
            # Create dictionary for card creation
            match_data = {
                "league": league,
                "prono": row["pronos"],
                "date": display_date,
                "time": row["time"],
                "teams": teams,
                "outcome": row["outcome"],
                "bookmaker": row["bookmaker"],
                "odds": row["odds"],
                "value": value,
                "prob": prob
            }
            
            formatted_data.append(match_data)
        
        return formatted_data
        
    def create_filter_controls(self, parent):
        """Create filter controls (simplified)"""
        return {}
        
    def display_data_cards(self):
        """Display data as cards with pagination"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        if self.data is None:
            if not self.load_data():
                return
                
        # If filtered_data is None, initialize it from data
        if self.filtered_data is None:
            self.filtered_data = self.data.copy()
        
        # Update page title
        self.title_label.configure(text="Value Bets")
                
        # Clean previous content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create filter controls (simplified in this version)
        self.filter_controls = self.create_filter_controls(self.content_frame)
        
        # Create main scroll frame
        scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent",
        )
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Prepare data for display
        formatted_matches = self.prepare_data_for_cards()
        
        self.current_page = 1
        
        # Display match count
        bets_count = len(self.filtered_data) if self.filtered_data is not None else 0
        total_count = len(self.data) if self.data is not None else 0
        
        count_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        count_frame.pack(fill="x", padx=15, pady=5)
        
        if bets_count < total_count:
            count_text = f"{bets_count} of {total_count} bets displayed"
        else:
            count_text = f"{bets_count} bets found"
            
        ctk.CTkLabel(
            count_frame,
            text=count_text,
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS["text_secondary"][mode_index]
        ).pack(side="left")
        
        # Function to change page
        def change_page(direction):
            if direction == "next" and self.current_page < self.pagination_controls["total_pages"]:
                self.current_page += 1
            elif direction == "prev" and self.current_page > 1:
                self.current_page -= 1
            elif direction == "refresh":
                # Just refresh the current page
                total_pages = max(1, (len(formatted_matches) + self.items_per_page - 1) // self.items_per_page)
                self.pagination_controls["total_pages"] = total_pages
                self.current_page = min(self.current_page, total_pages)
            
            self.pagination_controls["page_label"].configure(
                text=f"Page {self.current_page}/{self.pagination_controls['total_pages']}"
            )
            self.update_matches_display(
                self.current_page, 
                formatted_matches, 
                scroll_frame
            )
        
        # Create pagination controls
        pagination_frame = ctk.CTkFrame(self.content_frame, height=50, fg_color="transparent")
        pagination_frame.pack(fill="x", pady=(5, 15), padx=15)
        
        self.pagination_controls = self.create_pagination_controls(
            pagination_frame, 
            len(formatted_matches), 
            self.items_per_page, 
            change_page
        )
        
        # Display first page of matches
        self.update_matches_display(
            self.current_page, 
            formatted_matches, 
            scroll_frame
        )
    
    def show_statistics(self):
        """Show statistics and visualizations"""
        if self.data is None or self.data.empty:
            if not self.load_data():
                self.show_notification("No data available to generate statistics.", "warning")
                return
        
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        # Update title and clear content
        self.title_label.configure(text="Statistics & Visualizations")
        
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create stats container
        stats_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        stats_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Create top row with KPIs
        kpi_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        # Calculate KPIs
        total_bets = len(self.data)
        avg_odds = self.data["odds"].mean()
        
        # Traiter 'value' comme un float représentant un ratio, pas un pourcentage
        avg_value = self.data["value"].astype(float).mean()
        
        # Calculer un KPI supplémentaire: ROI potentiel moyen (value-1)
        avg_roi = (self.data["value"].astype(float) - 1).mean() * 100  # Convertir en pourcentage
        
        # Create KPI cards
        self.create_kpi_card(kpi_frame, "Total Value Bets", str(total_bets), "card-1")
        self.create_kpi_card(kpi_frame, "Average Odds", f"{avg_odds:.2f}", "card-2")
        self.create_kpi_card(kpi_frame, "Average Value", f"{avg_value:.2f}", "card-3")
        self.create_kpi_card(kpi_frame, "Avg. ROI", f"{avg_roi:.1f}%", "card-4")
        
        # Create charts container
        charts_container = ctk.CTkFrame(stats_container, fg_color="transparent")
        charts_container.pack(fill="both", expand=True)
        
        # Left chart: Value distribution (maintenant ratio, pas pourcentage)
        left_chart_frame = ctk.CTkFrame(
            charts_container, 
            fg_color=COLORS["card_bg"][mode_index],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"][mode_index]
        )
        left_chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        left_title = ctk.CTkLabel(
            left_chart_frame, 
            text="Value Distribution (Ratio)",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"][mode_index]
        )
        left_title.pack(pady=(15, 5))
        
        # Create value distribution chart
        fig1, ax1 = plt.subplots(figsize=(5, 4))
        
        # Extraire les données de value comme des floats
        value_data = self.data["value"].astype(float)
        
        # Créer des bins plus adaptés à des ratios
        bins = np.linspace(min(value_data), max(value_data), 10)
        
        ax1.hist(value_data, bins=bins, color=COLORS["accent"][0], alpha=0.7)
        ax1.set_xlabel('Value (ratio)')
        ax1.set_ylabel('Number of bets')
        ax1.grid(True, alpha=0.3)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # Ajouter une ligne verticale à value=2.0 qui représente un ROI de 100%
        ax1.axvline(x=2.0, color='red', linestyle='--', alpha=0.7)
        ax1.text(2.0, 0, '100% ROI', color='red', rotation=90, va='bottom', ha='right')
        
        fig1.tight_layout()
        
        # Embed chart in GUI
        canvas1 = FigureCanvasTkAgg(fig1, master=left_chart_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
        
        # Right chart: ROI potential distribution
        right_chart_frame = ctk.CTkFrame(
            charts_container, 
            fg_color=COLORS["card_bg"][mode_index],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"][mode_index]
        )
        right_chart_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        right_title = ctk.CTkLabel(
            right_chart_frame, 
            text="Distribution by Bookmaker",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"][mode_index]
        )
        right_title.pack(pady=(15, 5))
        
        # Create bookmaker distribution chart
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        
        # Get bookmaker counts
        bookmaker_counts = self.data['bookmaker'].value_counts()
        
        # Limit to top 10 bookmakers
        if len(bookmaker_counts) > 10:
            other_count = bookmaker_counts[10:].sum()
            bookmaker_counts = bookmaker_counts[:10]
            bookmaker_counts['Others'] = other_count
        
        bars = ax2.bar(bookmaker_counts.index, bookmaker_counts.values, color=COLORS["accent"][0], alpha=0.7)
        ax2.set_xlabel('Bookmaker')
        ax2.set_ylabel('Number of bets')
        
        # Fix the ticklabels warning by explicitly setting ticks first
        ax2.set_xticks(range(len(bookmaker_counts)))
        ax2.set_xticklabels(bookmaker_counts.index, rotation=45, ha='right')
        
        ax2.grid(True, axis='y', alpha=0.3)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=8)
                    
        fig2.tight_layout()
        
        # Embed chart in GUI
        canvas2 = FigureCanvasTkAgg(fig2, master=right_chart_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
        
        # Back button
        bottom_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkButton(
            bottom_frame,
            text="Back to Bets",
            command=self.display_data_cards,
            font=FONTS["button"],
            height=40,
            width=180,
            fg_color=COLORS["accent"][mode_index],
            hover_color=COLORS["accent_hover"][mode_index],
        ).pack(side="left")
    
    def create_kpi_card(self, parent, title, value, card_id):
        """Create a KPI card for the stats view"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        kpi_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card_bg"][mode_index],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"][mode_index],
            width=180,
            height=100
        )
        kpi_card.pack(side="left", padx=10, fill="both")
        kpi_card.pack_propagate(False)
        
        ctk.CTkLabel(
            kpi_card,
            text=title,
            font=ctk.CTkFont(family="Inter", size=14),
            text_color=COLORS["text_secondary"][mode_index]
        ).pack(pady=(15, 5))
        
        ctk.CTkLabel(
            kpi_card,
            text=value,
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=COLORS["text_primary"][mode_index]
        ).pack()
                
    def update_progress(self, progress_value, status_text):
        """Update progress bar and status text"""
        self.progress_bar.set(progress_value)
        self.progress_status.configure(text=status_text)
        self.update_idletasks()
        
    def _cleanup_after_scraping(self):
        """Clean up UI after scraping"""
        self.progress_frame.grid_forget()
        self.scrape_button.configure(state="normal")
        self.display_cards_button.configure(state="normal")
        self.stats_button.configure(state="normal")
    
    def load_data(self):
        """Load data from CSV file"""
        try:
            if os.path.exists(self.data_path):
                self.data = pd.read_csv(self.data_path)
                self.filtered_data = self.data.copy()
                return True
            else:
                self.show_notification("Data file not found. Run scraping first.", "warning")
                return False
        except Exception as e:
            self.show_notification(f"Error loading data: {str(e)}", "error")
            logger.exception(f"Error loading data: {str(e)}")  # logger.exception au lieu de logger.error avec exc_info
            return False
    
    def show_notification(self, message, type="info"):
        """Display a notification"""
        mode_index = 0 if ctk.get_appearance_mode().lower() == "light" else 1
        
        icon_map = {
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
            "info": "ℹ"
        }
        
        colors = {
            "success": COLORS["success_text"][mode_index],
            "warning": COLORS["warning_text"][mode_index],
            "error": COLORS["error_text"][mode_index],
            "info": COLORS["accent"][mode_index]
        }
        
        icon = icon_map.get(type, icon_map["info"])
        self.notification_label.configure(
            text=f"{icon} {message}",
            text_color=colors.get(type, colors["info"])
        )
        
if __name__ == "__main__":
    try:
        app = ValueBetScraperApp()
        
        # Properly handle potential after callbacks when app is destroyed
        def on_closing():
            plt.close('all')  # Close all matplotlib figures
            app.quit()
            app.destroy()
            
        app.protocol("WM_DELETE_WINDOW", on_closing)
        app.mainloop()
    except Exception as e:
        logger.exception(f"Uncaught exception in main thread: {str(e)}")