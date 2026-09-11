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

def merge_raw():
    print("Reading raw data folder...")

    # List only files in the directory
    files = [f.name for f in Path(raw_folder).iterdir() if f.is_file()]
    print(str(len(files)) + ' files found.')

    all_data = pd.DataFrame()

    invalid_entries = 0

    for file in files:
        csv_path = os.path.join(raw_folder, file)

        data = pd.read_csv(csv_path, low_memory=False)

        for _, line in data.iterrows():
            try:
                line['msmt_datetime'] = pd.to_datetime(line['msmt_datetime'], format = '%m/%d/%Y %H:%M')
            
            except Exception as e:
                invalid_entries += 1
                continue

        if (len(all_data) == 0):
            all_data = data
        else:
            all_data = pd.concat([all_data, data], ignore_index=True)

    if len(all_data) == 0:
        return

    save_path = cleaned_folder / Path("alldata" + now + ".csv")

    all_data.to_csv(save_path, index = True)

    print("New file created: " + str(save_path) + "")
    print(f"{len(all_data)} entries saved.")
    print(f"{invalid_entries} invalid measurements removed.")

if len(sys.argv) < 2:
    sys.exit("No arguments provided.")

command = sys.argv[1]
args = sys.argv[2:]

if (command == "merge"):
    merge_raw()