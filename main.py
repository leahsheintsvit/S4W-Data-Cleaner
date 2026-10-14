import pandas as pd
import datetime as dt
from pathlib import Path
import pathlib
from lxml import html
import os
import sys
from file_manager import try_read, try_save, backup_csv, try_save_tabs
from file_manager import raw_folder, cleaned_folder, backup_folder

dir = pathlib.Path().resolve()

raw_folder = dir / Path("Raw Data")
cleaned_folder = dir / Path("Cleaned Data")
backup_folder = dir / Path("Backup")

surface_path = raw_folder / Path("Flow_SW_DB.xlsx")
ground_path = raw_folder / Path("GW New Database.xlsx")
precip_path = raw_folder / Path("Precip_Database_2025.xlsx")

clean_surface_path = cleaned_folder / Path("Flow_SW_Clean.xlsx")
clean_ground_path = cleaned_folder / Path("GW_Clean.xlsx")
clean_precip_path = cleaned_folder / Path("Precip_2025_Clean.xlsx")

def clean_surface(): 
    print(f"Reading surface flow database: {surface_path}")

    xls = pd.ExcelFile(surface_path)

    sheets = xls.sheet_names
    print(f"{len(sheets)} sheets found in file")

    # Surface water file contains:
    # "Note" sheet
    # Measurement sheet for each stream

    discard_sheets = ["Note"]
    discard_columns = ["msmt_cmnts_original", "water_level_image", "water_flow_image", "water_flow_cmnts", "msmt_cmnts", "*meta-instance-id*"]
    discard_missing = ["msmt_datetime", "geopoint:Longitude", "geopoint:Latitude"]

    stream_names = [name for name in sheets if name not in discard_sheets]

    all_data = try_read(surface_path)

    # Classify per-stream data and merge into a single sheet

    all_output = pd.DataFrame()

    for i in range(len(stream_names)):

        name = stream_names[i]

        stream_data = (
            all_data[name]
            .drop(columns=discard_columns)
            .dropna(subset=discard_missing)
        )

        entries = len(stream_data)

        stream_data.insert(0, "stream_source", [name] * entries)

        if len(all_output) == 0:
            all_output = stream_data
        else:
            all_output = pd.concat(
                [all_output, stream_data],
                axis=0
            )

    all_output["msmt_datetime"] = pd.to_datetime(all_output["msmt_datetime"], errors = "coerce")

    all_output = (
        all_output
        .sort_values(by=["stream_source", "msmt_datetime"], ascending=True)
    )

    try_save(all_output, clean_surface_path)

def clean_ground():
    print(f"Reading groundwater database: {ground_path}")

    # Information about each site

    site_info = try_read(ground_path, "Site_IDs")

    site_info.insert(0, "GW_ID", site_info["Site_IDs"])

    site_info = (
        site_info
        .drop(columns=["Site_IDs", "Data-Range", "Corresponding DHM station"])
    )

    # Merged groundwater data from S4W Nepal

    all_data = try_read(ground_path, "Merged")

    fields = ["GW_ID", "siteDesc", "Latitude", "Longitude", "RP to GS", "New RP to GS", "Date of Modification"]

    dated_columns = [column for column in all_data.columns if column not in fields]

    entries = []

    for _, entry in all_data.iterrows():

        gw_id = entry["GW_ID"]

        for i in range(len(dated_columns)):

            if pd.notna(entry[dated_columns[i]]):
                
                msmt = entry[dated_columns[i]]

                year = dated_columns[i].split("_")[0]
                month = dated_columns[i].split("_")[1]

                new_entry = {"GW_ID": gw_id, "Year": year, "Month": month, "GW_msmt": msmt}
                entries.append(new_entry)

    all_output = pd.DataFrame(entries)

    all_output = (
        pd.merge(all_output, site_info, on="GW_ID", how="inner")
        .sort_values(by=["Year", "Month", "GW_ID"], ascending=True)
    )

    yearly_monthly_avg = (
        all_output.groupby(["Year", "Month"])
        .agg(
            GW_mean=("GW_msmt", "mean"),
            GW_std=("GW_msmt", "std"),
            GW_count=("GW_msmt", "count")
        )
        .reset_index()
    )

    all_time_monthly_average = (
        all_output.groupby(["Month"])
        .agg(
            GW_mean=("GW_msmt", "mean"),
            GW_std=("GW_msmt", "std"),
            GW_count=("GW_msmt", "count")
        )
        .reset_index()
    )

    tabs = [all_output, yearly_monthly_avg, all_time_monthly_average]
    tab_names = ["Full Data", "Yearly Averages", "All-Time Averages"]

    try_save_tabs(tabs, tab_names, clean_ground_path)

clean_ground()