import customtkinter as ctk
from CTkTable import CTkTable
import pandas as pd
import os
from loguru import logger
from tkinter import Menu

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Value Bets Scraper")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = int(screen_width * 0.75)
        height = int(screen_height * 0.75)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.logger = logger
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.label = ctk.CTkLabel(self.main_frame, text="Value Bets Data:")
        self.label.pack(pady=10)

        self.display_button = ctk.CTkButton(
            self.main_frame, 
            text="Display Value Bets", 
            command=self.display_csv_content
        )
        self.display_button.pack(pady=10)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, width=1150, height=600)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.table = None
        self.cached_data = None  # Cache for CSV data
        self.create_menubar()

    def create_menubar(self):
        menubar = Menu(self)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Quit", command=self.quit_app)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def quit_app(self):
        self.logger.info("Exiting application...")
        self.destroy()

    def load_csv_data(self):
        """Loads and processes the CSV data, caching it for reuse."""
        if self.cached_data is not None:
            return self.cached_data

        input_file = os.path.join(os.path.dirname(__file__), "../data/oddsportal_data_no_login.csv")

        if not os.path.exists(input_file):
            self.logger.error(f"File not found: {input_file}")
            return None

        df = pd.read_csv(input_file)
        df = df.drop(columns=["time", "countries"], errors="ignore")

        if "probability" in df.columns:
            df = df[df["probability"] >= 50]

        df.columns = df.columns.str.replace("team_1", "home").str.replace("team_2", "away")
        self.cached_data = df
        return df

    def display_csv_content(self):
        self.logger.info("Displaying CSV content...")

        df = self.load_csv_data()
        if df is None or df.empty:
            self.logger.error("No data to display.")
            return

        headers = [col.upper() for col in df.columns.tolist()]
        data = df.values.tolist()
        table_data = [headers] + data

        if self.table is not None:
            self.table.destroy()

        # Use fixed column widths for simplicity
        column_widths = [150] * len(headers)

        self.table = CTkTable(
            master=self.scrollable_frame,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            header_color="gray70",
            hover_color="gray90",
            corner_radius=5,
        )
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

        self.logger.info("Table displayed successfully")

if __name__ == "__main__":
    app = App()
    app.mainloop()
