# test_parser.py
from parser.parse_990 import run_990_parser

# Path to your source CSV with XML links
source_csv = '/Users/jacobplaza/Library/CloudStorage/OneDrive-SEIULOCAL73/Test Folder/data/data_source.csv'

# Path to your results folder
results_folder = '/Users/jacobplaza/Library/CloudStorage/OneDrive-SEIULOCAL73/Test Folder/results'

# Call the parser function
run_990_parser(source_csv, results_folder)

print("Parsing complete! Check the results folder for CSV outputs and HTML summary.")
