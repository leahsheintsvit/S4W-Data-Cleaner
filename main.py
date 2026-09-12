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

shared_fields = ["msmt_datetime", "geopoint:Latitude", "geopoint:Longitude", "QCFlag"]
shared_identifiers = ["*meta-instance-id*", "*meta-submission-date*", "_id", "deviceid", "AutoSiteID", "MonID", "collection"]



def clean_raw():
    print("Reading raw data folder...")

    # List only files in the directory
    files = [f.name for f in Path(raw_folder).iterdir() if f.is_file()]
    print(str(len(files)) + ' files found.')

    all_data = pd.DataFrame()

    invalid_entries = 0

    for file in files:
        csv_path = os.path.join(raw_folder, file)

        data = pd.read_csv(csv_path, low_memory=False)

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

        clean_data = data.dropna(subset=["msmt_datetime"]).copy()
        clean_data = clean_data[final_columns]
        clean_data = clean_data.sort_values(by='msmt_datetime', ascending=False)

        save_path = cleaned_folder / Path(file.split(".", 1)[0] + "-cleaned.csv")

        try:
            clean_data.to_csv(save_path, index = False)

        except Exception as e:
            print(f"Failed to write to path: {save_path}. Is this file open in Excel?")

            continue
        
        print(f"New file created: {save_path}")
        print(f"{len(data) - len(clean_data)} invalid entries removed.")

if len(sys.argv) < 2:
    sys.exit("No arguments provided.")

command = sys.argv[1]
args = sys.argv[2:]

if (command == "clean"):
    clean_raw()