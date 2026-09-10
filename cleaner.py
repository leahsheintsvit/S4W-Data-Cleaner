import pandas as pd
import datetime as dt
from pathlib import Path
from lxml import html
import os

dir = pathlib.Path().resolve()

now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
raw_folder = dir / Path("Raw Data")
cleaned_folder = dir / Path("Cleaned Data")

def merge_raw():
    print("Reading raw data folder...")

    # List only files in the directory
    files = [f.name for f in Path(permit_input_folder).iterdir() if f.is_file()]
    print(str(len(files)) + ' files found.')

    for file in files:
        csv_path = os.path.join(raw_folder, file)

        try:
            data = pd.read_csv(csv_path, low_memory=False)

            #save_path = cleaned_folder / Path(file.split("-", 1)[0] + "-cleaned-" + now)
            #

            data['msmt-datetime'] = pd.to_datetime(data['msmt-datetime'], format = '%m/%d/%Y %H:%M')

            if (len(all_data) == 0):
                all_data = data
            else:
                all_data = pd.concat([all_data, data], ignore_index=True)
            
        except Exception as e:
            print(f"Could not read: {csv_path}.")
            continue

    save_path = cleaned_folder / Path("merged-" + now)

    all_data.to_csv(save_path, index = True)

if len(sys.argv) < 2:
    sys.exit("No arguments provided.")

command = sys.argv[1]
args = sys.argv[2:]

if (command == "merge"):
    merge_raw()