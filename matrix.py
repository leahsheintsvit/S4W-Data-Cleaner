import pandas as pd
import datetime as dt
from pathlib import Path
import pathlib
from lxml import html
import os
import sys
from file_manager import try_read, try_save, backup_csv, try_save_tabs
from file_manager import raw_folder, cleaned_folder, backup_folder
from main import clean_ground_path, clean_surface_path

availability_matrix_path = cleaned_folder / Path("Data Availability Matrix.xlsx")

# Aggregated by Month

#           Year, Mon --------
# Station ID
# |         [data1, data2, data3]
# |
# |

def generate_matrix():

    ground_cleaned = (
        try_read(clean_ground_path)["Cleaned Data"]
        .sort_values(by="site_id")
    )

    surface_cleaned = (
        try_read(clean_surface_path)["Cleaned Data"]
        .sort_values(by="site_id")
    )


    #tabs = [ground_data]
    #tab_names = ["Groundwater Matrix"]
    #try_save_tabs(tabs, tab_names, availability_matrix_path)

generate_matrix()