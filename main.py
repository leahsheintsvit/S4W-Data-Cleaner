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

    entry_totals = []

    for i in range(len(stream_names)):

        name = stream_names[i]

        stream_data = all_data[name]

        if len(stream_data) > 0:
            entry_totals.append(len(all_data[name]))
        else:
            entry_totals.append(0)

        stream_data.insert(0, "stream_source", [name] * len(all_data[name]))

        if len(all_output) == 0:
            all_output = stream_data
        else:
            all_output = pd.concat(
                [all_output, stream_data],
                axis=0
            )

    all_output["msmt_datetime"] = pd.to_datetime(all_output["msmt_datetime"], errors = "coerce")

    all_output.insert(2, "Year", all_output["msmt_datetime"].dt.year)
    all_output.insert(3, "Month", all_output["msmt_datetime"].dt.month)

    site_info = (
        all_output.groupby(["stream_source"])
        .agg(
            lat_mean=("geopoint:Latitude", "mean"),
            lat_min=("geopoint:Latitude", "min"),
            lat_max=("geopoint:Latitude", "max"),
            long_mean=("geopoint:Longitude", "mean"),
            long_min=("geopoint:Longitude", "min"),
            long_max=("geopoint:Longitude", "max"),
            alt_mean=("geopoint:Altitude", "mean"),
            alt_min=("geopoint:Altitude", "min"),
            alt_max=("geopoint:Altitude", "max"),
            num=("stream_source", "count"),
            project=("Project", "first")  
        )
        .reset_index()
    )

    all_output["water_flow_cms"] = pd.to_numeric(all_output["water_flow_cms"], errors="coerce")

    stream_yearly_stats = (
        all_output.groupby(["stream_source", "Year"])["water_flow_cms"]
        .describe()
        .reset_index()
    )

    grouped_yearly_stats = (
        all_output.groupby(["Year"])["water_flow_cms"]
        .describe()
        .reset_index()
    )

    all_output = (
        all_output
        .drop(columns=discard_columns)
        .dropna(subset=discard_missing)
        .sort_values(by=["stream_source", "msmt_datetime"], ascending=True)   
    )

    tabs = [all_output, site_info, stream_yearly_stats, grouped_yearly_stats, all_data["Note"]]
    tab_names = ["Cleaned Data", "Stream Info", "Per-Stream Flow Stats", "Grouped Flow Stats", "Note From Sponsors"]

    try_save_tabs(tabs, tab_names, clean_surface_path)

def clean_ground():
    print(f"Reading groundwater database: {ground_path}")

    # Information about each site

    site_info = try_read(ground_path, "Site_IDs")

    site_info.insert(0, "GW_ID", site_info["Site_IDs"])

    site_info = (
        site_info
        .drop(columns=["Site_IDs"])
    )

    to_merge = (
        site_info
        .drop(columns=["Location", "District", "Watershed", "Purpose", "Landuse", "Status", "Data-Range", "Corresponding DHM station"])
    )

    # Merged groundwater data from S4W Nepal

    all_data = try_read(ground_path)
    merged = all_data["Merged"]

    fields = ["GW_ID", "siteDesc", "Latitude", "Longitude", "RP to GS", "New RP to GS", "Date of Modification"]

    dated_columns = [column for column in merged.columns if column not in fields]

    entries = []
    new_info = []

    for _, entry in merged.iterrows():

        gw_id = entry["GW_ID"]
        msmt_count = 0

        for i in range(len(dated_columns)):

            if pd.notna(entry[dated_columns[i]]):
                
                msmt = entry[dated_columns[i]]

                year = dated_columns[i].split("_")[0]
                month = dated_columns[i].split("_")[1]

                msmt_count += 1

                new_entry = {"GW_ID": gw_id, "Year": year, "Month": month, "GW_msmt": msmt}
                entries.append(new_entry)

        info_line = {"GW_ID": gw_id, "Total": msmt_count}
        new_info.append(info_line)

    all_output = pd.DataFrame(entries)

    all_output = (
        pd.merge(all_output, to_merge, on="GW_ID", how="inner")
        .sort_values(by=["Year", "Month", "GW_ID"], ascending=True)
    )

    monthly_avg = (
        all_output.groupby(["Year", "Month"])["GW_msmt"]
        .describe()
        .reset_index()
    )

    per_site_avg = (
        all_output.groupby(["GW_ID", "Year"])["GW_msmt"]
        .describe()
        .reset_index()
    )

    new_info_df = pd.DataFrame(new_info)
    
    site_info = (
        pd.merge(site_info, new_info_df, on="GW_ID", how="inner")
        .sort_values(by="GW_ID")
    )

    tabs = [merged, all_output, monthly_avg, per_site_avg, site_info, all_data["Note"]]
    tab_names = ["Raw Data", "Cleaned Data", "Monthly Levels", "Grouped Site Levels", "Site Info", "Note From Sponsors"]

    try_save_tabs(tabs, tab_names, clean_ground_path)

def clean_precip():
    print(f"Reading precipitation data: {precip_path}")

    all_data = try_read(precip_path)

    precip_data = all_data["From_Web_App"]

    meta_columns = ["MonID", "Latitude", "Longitude", "No_msmt"]

    dated = precip_data.drop(columns=meta_columns)

    measurements = []

    for _, entry in precip_data.iterrows():

        mon_id = entry["MonID"]
        lat = entry["Latitude"]
        long = entry["Longitude"]

        for column in dated.columns:
            msmt = entry[column]

            new_msmt = {"MonID": mon_id, "Latitude": lat, "Longitude": long, "Year": 2025, "Date": column, "precip_mm": msmt}

            measurements.append(new_msmt)

    measurements = pd.DataFrame(measurements)

    per_cs_stats = (
        measurements.groupby("MonID")["precip_mm"]
        .describe()
        .reset_index()
    )

    grouped_daily_stats = (
        measurements.groupby("Date")["precip_mm"]
        .describe()
        .reset_index()
    )

    cs_info = all_data["CS_Information"]

    tabs = [precip_data, per_cs_stats, grouped_daily_stats, cs_info, all_data["Note"]]
    tab_names = ["Raw Data", "Per-CS Precip (mm)", "Daily Grouped Precip (mm)", "CS Information", "Note From Sponsors"]

    try_save_tabs(tabs, tab_names, clean_precip_path)

clean_ground()