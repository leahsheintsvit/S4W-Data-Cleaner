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

shared_fields = ["msmt_datetime", "geopoint:Latitude", "geopoint:Longitude", "QCFlag"]
shared_identifiers = ["*meta-instance-id*", "*meta-submission-date*", "_id", "deviceid", "AutoSiteID", "MonID", "collection"]

nepal_lat_min = 26.35
nepal_lat_max = 30.45
nepal_lon_min = 80.00
nepal_lon_max = 88.20


def clean_raw():
    print("Reading raw data folder...")

    # List only files in the directory
    files = [f.name for f in Path(raw_folder).iterdir() if f.is_file()]
    print(str(len(files)) + ' files found.')

    for file in files:
        csv_path = os.path.join(raw_folder, file)

        data = try_read(csv_path)

        data_columns = data.columns.values.tolist()

        unique_columns = [column for column in data_columns if column not in shared_fields and column not in shared_identifiers]

        image_columns = [column for column in unique_columns if "image" in column]
        msmt_columns = [column for column in unique_columns if column not in image_columns]

        final_columns = msmt_columns + image_columns + shared_fields + shared_identifiers

        data["msmt_datetime"] = pd.to_datetime(
            data["msmt_datetime"],
            format="%m/%d/%Y %H:%M",
            errors="coerce"
        )

        # Remove entries outside of Nepal's bounding box
        clean_data = data[
            (
                data["geopoint:Latitude"].between(nepal_lat_min, nepal_lat_max) & 
                data["geopoint:Longitude"].between(nepal_lon_min, nepal_lat_max)
            )
        ].copy()

        clean_data = data.dropna(subset=["msmt_datetime"]).copy()
        clean_data = clean_data[final_columns]
        clean_data = clean_data.sort_values(by='msmt_datetime', ascending=False)

        save_path = cleaned_folder / Path(file.split(".", 1)[0] + "-cleaned.csv")

        try_save(clean_data, save_path)
        
        print(f"New file created: {save_path}")
        print(f"{len(data) - len(clean_data)} invalid entries removed.")

def try_save(df, path):
    try:
        df.to_csv(path, index = False)
    except Exception as e:
        print(f"Failed to save to path: {path}")
        backup_csv(df)
        sys.exit()

def try_read(path):
    try:
        df = pd.read_csv(path, low_memory=False)
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

clean_raw()