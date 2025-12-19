import tkinter as tk
from tkinter import filedialog, scrolledtext
import threading
from parser.parse_990 import run_990_parser

class GUI:
    def __init__(self, master):
        self.master = master
        master.title("Form 990 Parser")
        master.geometry("700x500")
        master.resizable(False, False)

        # Container frame (lets OS theme shine)
        container = tk.Frame(master)
        container.pack(padx=20, pady=20, fill="both", expand=True)

        # Buttons
        self.btn_browse = tk.Button(
            container,
            text="Browse CSV",
            command=self.browse_csv
        )
        self.btn_browse.pack(pady=5)

        self.btn_select_folder = tk.Button(
            container,
            text="Select Destination Folder",
            command=self.select_folder
        )
        self.btn_select_folder.pack(pady=5)

        self.btn_run = tk.Button(
            container,
            text="Run Parser",
            command=self.run_parser_thread
        )
        self.btn_run.pack(pady=(5, 15))

        # Log box
        self.log = scrolledtext.ScrolledText(
            container,
            width=80,
            height=15,
            state='disabled'
        )
        self.log.pack(fill="both", expand=True)

        # Initialize paths
        self.source_csv = ""
        self.results_dir = ""

    # --- Functions ---
    def browse_csv(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")]
        )
        if file_path:
            self.source_csv = file_path
            self.log_message(f"Selected CSV: {file_path}")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.results_dir = folder_path
            self.log_message(f"Selected destination folder: {folder_path}")

    def run_parser_thread(self):
        if not self.source_csv or not self.results_dir:
            self.log_message("Please select CSV and destination folder first.")
            return
        threading.Thread(target=self.run_parser, daemon=True).start()

    def run_parser(self):
        self.log_message("Starting parser...")
        try:
            outputs = run_990_parser(self.source_csv, self.results_dir)
            self.log_message("Parsing complete!")
            for k, v in outputs.items():
                self.log_message(f"{k}: {v}")
        except Exception as e:
            self.log_message(f"Error: {str(e)}")

    # --- Logging (thread-safe) ---
    def log_message(self, message):
        self.master.after(0, self._update_log, message)

    def _update_log(self, message):
        self.log.configure(state='normal')
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    GUI(root)
    root.mainloop()
