import pandas as pd
import datetime as dt
from pathlib import Path
import pathlib
from lxml import html
import os
import sys

dir = pathlib.Path().resolve()

now = dt.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
raw_folder = dir / Path("Raw Data")
cleaned_folder = dir / Path("Cleaned Data")
backup_folder = dir / Path("Backup")

surface_path = raw_folder / Path("Flow_SW_DB.xlsx")
ground_path = raw_folder / Path("GW New Database.xlsx")
precip_path = raw_folder / Path("Precip_Database_2025.xlsx")
raw_path = raw_folder / Path("Raw data.xlsx")

def clean_surface(): 
    print(f"Reading surface flow database: {surface_path}")

def try_save(df, path):
    try:
        type = path.split(".")[1]
        if type == "xlsx":
            df.to_excel(path, index = False)
        elif type == "csv":
            df.to_csv(path, index = False)
        else:
            print(f"{type} is not a recognized extension")
            backup_csv(df)
            sys.exit()
        
    except Exception as e:
        print(f"Failed to save to path: {path}")
        backup_csv(df)
        sys.exit()

def try_read(path):
    try:
        type = path.split(".")[1]
        if type == "xlsx":
            df = pd.read_excel(path, low_memory=False)
        elif type == "csv":
            df = pd.read_csv(path, low_memory=False)
        else:
            print(f"{type} is not a recognized extension")
            sys.exit()
        return df
    except Exception as e:
        print(f"Failed to read file at path: {path}")
        sys.exit()

def backup_csv(df):
    now = dt.datetime.now().strftime(format="%d%m%Y%H%M%S")
    backup_path = backup_folder / Path(f"backup-{now}.csv")

    try:
        df.to_csv(backup_path, index = False)
        print(f"Backup created: {backup_path}")
    except Exception as e:
        print(f"Backup failed: {e}")

clean_surface()