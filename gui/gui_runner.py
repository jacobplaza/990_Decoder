import tkinter as tk
from tkinter import filedialog, scrolledtext
import threading
import os

from parser.parse_990 import run_990_parser


class GUI:

    def __init__(self, master):

        self.master = master

        master.title(
            "Form 990 Parser"
        )

        master.geometry(
            "700x550"
        )

        master.resizable(
            False,
            False
        )

        # -----------------------------------------------------
        # Container frame
        # -----------------------------------------------------

        container = tk.Frame(
            master
        )

        container.pack(
            padx=20,
            pady=20,
            fill="both",
            expand=True
        )

        # -----------------------------------------------------
        # Select XML source folder
        # -----------------------------------------------------

        self.btn_browse = tk.Button(
            container,
            text="Select XML Source Folder",
            command=self.select_xml_folder
        )

        self.btn_browse.pack(
            pady=5
        )

        # -----------------------------------------------------
        # Select destination folder
        # -----------------------------------------------------

        self.btn_select_folder = tk.Button(
            container,
            text="Select Destination Folder",
            command=self.select_folder
        )

        self.btn_select_folder.pack(
            pady=5
        )

        # -----------------------------------------------------
        # Run parser
        # -----------------------------------------------------

        self.btn_run = tk.Button(
            container,
            text="Run Parser",
            command=self.run_parser_thread
        )

        self.btn_run.pack(
            pady=(5, 15)
        )

        # -----------------------------------------------------
        # Log box
        # -----------------------------------------------------

        self.log = scrolledtext.ScrolledText(
            container,
            width=80,
            height=18,
            state="disabled"
        )

        self.log.pack(
            fill="both",
            expand=True
        )

        # -----------------------------------------------------
        # Initialize paths
        # -----------------------------------------------------

        self.xml_dir = ""

        self.results_dir = ""

    # =========================================================
    # Select XML source folder
    # =========================================================

    def select_xml_folder(self):

        folder_path = (
            filedialog.askdirectory(
                title="Select Folder Containing XML Files"
            )
        )

        if folder_path:

            self.xml_dir = folder_path

            # Count XML files in selected folder
            xml_count = 0

            try:

                for filename in os.listdir(
                    folder_path
                ):

                    full_path = os.path.join(
                        folder_path,
                        filename
                    )

                    if (
                        os.path.isfile(
                            full_path
                        )
                        and filename.lower().endswith(
                            ".xml"
                        )
                    ):
                        xml_count += 1

            except Exception as e:

                self.log_message(
                    f"Error reading source folder: {e}"
                )

                return

            self.log_message(
                f"Selected XML source folder: "
                f"{folder_path}"
            )

            self.log_message(
                f"Found {xml_count} XML file(s)."
            )

    # =========================================================
    # Select destination folder
    # =========================================================

    def select_folder(self):

        folder_path = (
            filedialog.askdirectory(
                title="Select Destination Folder"
            )
        )

        if folder_path:

            self.results_dir = folder_path

            self.log_message(
                f"Selected destination folder: "
                f"{folder_path}"
            )

    # =========================================================
    # Start parser in background thread
    # =========================================================

    def run_parser_thread(self):

        # -----------------------------------------------------
        # Validate XML source folder
        # -----------------------------------------------------

        if not self.xml_dir:

            self.log_message(
                "Please select the XML source folder first."
            )

            return

        # -----------------------------------------------------
        # Validate destination folder
        # -----------------------------------------------------

        if not self.results_dir:

            self.log_message(
                "Please select the destination folder first."
            )

            return

        # -----------------------------------------------------
        # Disable buttons while processing
        # -----------------------------------------------------

        self.btn_browse.config(
            state="disabled"
        )

        self.btn_select_folder.config(
            state="disabled"
        )

        self.btn_run.config(
            state="disabled"
        )

        # -----------------------------------------------------
        # Start parser in background
        # -----------------------------------------------------

        threading.Thread(
            target=self.run_parser,
            daemon=True
        ).start()

    # =========================================================
    # Run parser
    # =========================================================

    def run_parser(self):

        self.log_message(
            ""
        )

        self.log_message(
            "==================================="
        )

        self.log_message(
            "Starting Form 990 parser..."
        )

        self.log_message(
            "==================================="
        )

        self.log_message(
            f"XML source folder: "
            f"{self.xml_dir}"
        )

        self.log_message(
            f"Results folder: "
            f"{self.results_dir}"
        )

        self.log_message(
            ""
        )

        try:

            outputs = run_990_parser(
                xml_dir=self.xml_dir,
                results_dir=self.results_dir,
                progress_callback=self.log_message
            )

            self.log_message(
                ""
            )

            self.log_message(
                "Parser finished successfully."
            )

            self.log_message(
                ""
            )

            self.log_message(
                "Output files:"
            )

            for key, value in outputs.items():

                self.log_message(
                    f"{key}: {value}"
                )

        except Exception as e:

            self.log_message(
                ""
            )

            self.log_message(
                "==================================="
            )

            self.log_message(
                "PARSER ERROR"
            )

            self.log_message(
                "==================================="
            )

            self.log_message(
                str(e)
            )

        finally:

            # -------------------------------------------------
            # Re-enable buttons
            # -------------------------------------------------

            self.master.after(
                0,
                self.enable_buttons
            )

    # =========================================================
    # Re-enable GUI buttons
    # =========================================================

    def enable_buttons(self):

        self.btn_browse.config(
            state="normal"
        )

        self.btn_select_folder.config(
            state="normal"
        )

        self.btn_run.config(
            state="normal"
        )

    # =========================================================
    # Thread-safe logging
    # =========================================================

    def log_message(
        self,
        message
    ):

        self.master.after(
            0,
            self._update_log,
            message
        )

    # =========================================================
    # Update log window
    # =========================================================

    def _update_log(
        self,
        message
    ):

        self.log.configure(
            state="normal"
        )

        self.log.insert(
            tk.END,
            message + "\n"
        )

        self.log.see(
            tk.END
        )

        self.log.configure(
            state="disabled"
        )


# =============================================================
# Start application
# =============================================================

if __name__ == "__main__":

    root = tk.Tk()

    GUI(
        root
    )

    root.mainloop()
