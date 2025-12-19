import tkinter as tk
from tkinter import filedialog, scrolledtext, font
import threading
from parser.parse_990 import run_990_parser  # Your parser function

class GUI:
    def __init__(self, master):
        self.master = master
        master.title("Form 990 Parser")
        master.configure(bg="#228B22")  # Forest green background
        master.geometry("700x500")

        # Fonts
        btn_font = font.Font(family="Arial", size=12, weight="bold")
        log_font = font.Font(family="Courier", size=10)

        # Buttons
        self.btn_browse = tk.Button(master, text="Browse CSV", command=self.browse_csv, font=btn_font, bg="#006400", fg="white")
        self.btn_browse.pack(pady=10)

        self.btn_select_folder = tk.Button(master, text="Select Destination Folder", command=self.select_folder, font=btn_font, bg="#006400", fg="white")
        self.btn_select_folder.pack(pady=10)

        self.btn_run = tk.Button(master, text="Run Parser", command=self.run_parser_thread, font=btn_font, bg="#006400", fg="white")
        self.btn_run.pack(pady=10)

        # Log box
        self.log = scrolledtext.ScrolledText(master, width=80, height=15, font=log_font)
        self.log.pack(pady=10)
        self.log.configure(bg="#006400", fg="white", insertbackground="white", state='disabled')

        # Initialize paths
        self.source_csv = ""
        self.results_dir = ""

    # --- Functions ---
    def browse_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.source_csv = file_path
            self.log_message(f"Selected CSV: {file_path}")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.results_dir = folder_path
            self.log_message(f"Selected destination folder: {folder_path}")

    def run_parser_thread(self):
        # Run parser in separate thread to avoid freezing GUI
        if not self.source_csv or not self.results_dir:
            self.log_message("Please select CSV and destination folder first.")
            return
        t = threading.Thread(target=self.run_parser)
        t.start()

    def run_parser(self):
        self.log_message("Starting parser...")
        try:
            outputs = run_990_parser(self.source_csv, self.results_dir)
            self.log_message("Parsing complete!")
            self.log_message(f"People CSV: {outputs['people_csv']}")
            self.log_message(f"Orgs CSV: {outputs['orgs_csv']}")
            self.log_message(f"Financial CSV: {outputs['financial_csv']}")
            self.log_message(f"Financial Changes CSV: {outputs['financial_changes_csv']}")
            self.log_message(f"HTML Summary: {outputs['html_summary']}")
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

# --- Run GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    gui = GUI(root)
    root.mainloop()
