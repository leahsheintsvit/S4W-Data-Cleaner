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

data_folder = dir / Path("data")
raw_folder = data_folder / Path("raw")
cleaned_folder = data_folder / Path("clean")

app_folder = dir / Path("app")
script_folder = dir / Path("scripts")
page_folder = dir / Path("pages")

backup_folder = dir / Path("backup")

surface_path = raw_folder / Path("Flow_SW_DB.xlsx")
ground_path = raw_folder / Path("GW New Database.xlsx")
precip_path = raw_folder / Path("Precip_Database_2025.xlsx")

clean_surface_path = cleaned_folder / Path("SW_Clean.xlsx")
clean_ground_path = cleaned_folder / Path("GW_Clean.xlsx")
clean_precip_path = cleaned_folder / Path("Precip_2025_Clean.xlsx")

master_sites_path = cleaned_folder / Path("All_Sites.xlsx")
g_sites_path = cleaned_folder / Path("Ground_Sites.xlsx")

# • List all stations by dataset (ID, name, lat/lon, elevation, watershed, start/end date, time step)
    # Do this for ground and surface water right now; no full access to precipitation
# • Define dashboard users (S4W team, researchers)
# • Sketch page layout (Home, Temporal, Spatial, Integrated, Data/Download)
# • Set up GitHub repo, Python environment (requirements.txt), folder structure (data/raw, data/clean, app/pages)

def clean_surface(): 
    print(f"Reading surface flow database: {surface_path}")

    # Open 
    xls = pd.ExcelFile(surface_path)

    sheets = xls.sheet_names

    site_ids = [site_id for site_id in sheets if site_id not in ["Note"]]

    all_data = try_read(surface_path)

    all_output = pd.DataFrame()

    entry_totals = []

    for i in range(len(site_ids)):

        site_id = site_ids[i]

        stream_data = all_data[site_id]

        if len(stream_data) > 0:
            entry_totals.append(len(all_data[site_id]))
        else:
            entry_totals.append(0)

        stream_data.insert(0, "site_id", [site_id] * len(all_data[site_id]))

        if len(all_output) == 0:
            all_output = stream_data
        else:
            all_output = pd.concat(
                [all_output, stream_data],
                axis=0
            )

    all_output["msmt_datetime"] = pd.to_datetime(all_output["msmt_datetime"], errors = "coerce")

    site_info = (
        all_output.groupby(["site_id"])
        .agg(
            lat_med=("geopoint:Latitude", "median"),
            long_med=("geopoint:Longitude", "median"),
            alt_med=("geopoint:Altitude", "median"),
            num=("site_id", "count"),
            project=("Project", "first")  
        )
        .reset_index()
    )

    all_time_coverage = (
        all_output.groupby(["site_id"])
        .agg(
            first_date=("msmt_datetime", "min"),
            last_date=("msmt_datetime", "max"),
        )
        .reset_index()
    )

    all_time_coverage["target_time_step"] = ["1 month"] * len(all_time_coverage)

    site_info = (
        pd.merge(site_info, all_time_coverage, on="site_id", how="inner")
        .sort_values(by=["site_id"])
        .reset_index(drop=True)
    )

    all_output.insert(1, "year", pd.to_datetime(all_output["msmt_datetime"], errors="coerce").dt.year)
    all_output.insert(2, "month", pd.to_datetime(all_output["msmt_datetime"], errors="coerce").dt.month)

    discard_missing = ["msmt_datetime"]
    
    old_pos_columns = ["geopoint:Altitude", "geopoint:Latitude", "geopoint:Longitude"]
    new_pos_columns = ["Altitude", "Latitude", "Longitude"]
    
    all_output[new_pos_columns] = all_output[old_pos_columns]

    all_output = (
        all_output
        .sort_values(by=["site_id", "msmt_datetime"], ascending=True)   
    )


    tabs = [all_output, site_info, all_data["Note"]]
    tab_names = ["Cleaned Data", "Site Info", "Note From Sponsors"]

    try_save_tabs(tabs, tab_names, clean_surface_path)

def clean_ground():
    print(f"Reading groundwater database: {ground_path}")

    # Information about each site

    site_info = try_read(ground_path, "Site_IDs")
    merged = try_read(ground_path, "Merged")

    site_info.insert(0, "site_id", site_info["Site_IDs"])
    merged.insert(0, "site_id", merged["GW_ID"])

    site_info = (
        site_info
        .drop(columns="Site_IDs")
        .reset_index(drop=True)
    )

    merged = (
        merged
        .drop(columns="GW_ID")
        .reset_index(drop=True)
    )

    to_merge = (
        site_info
        .drop(columns=["Location", "District", "Watershed", "Purpose", "Landuse", "Status", "Data-Range", "Corresponding DHM station"])
    )

    fields = ["site_id", "siteDesc", "Latitude", "Longitude", "RP to GS", "New RP to GS", "Date of Modification"]

    dated_columns = [column for column in merged.columns if column not in fields]

    entries = []
    new_info = []

    for _, entry in merged.iterrows():

        site_id = entry["site_id"]

        if pd.notna(entry["New RP to GS"]):
            rp2gs = entry["New RP to GS"]
            rp2gs_modified = entry["Date of Modification"]
        else:
            rp2gs = entry["RP to GS"]
            rp2gs_modified = None

        msmt_count = 0

        for i in range(len(dated_columns)):

            if pd.notna(entry[dated_columns[i]]):
                
                msmt = entry[dated_columns[i]]

                year = dated_columns[i].split("_")[0]
                month = dated_columns[i].split("_")[1]

                msmt_count += 1

                new_entry = {"site_id": site_id, "year": year, "month": month, "water_depth": msmt}
                entries.append(new_entry)

        info_line = {"site_id": site_id, "RP to GS": rp2gs, "RP to GS Last Modified": rp2gs_modified, "total": msmt_count} # Add rp-gs to info
        new_info.append(info_line)

    all_output = pd.DataFrame(entries)

    all_output = (
        pd.merge(all_output, to_merge, on="site_id", how="inner")
        .sort_values(by=["year", "month", "site_id"], ascending=True)
        .reset_index(drop=True)
    )

    new_info_df = pd.DataFrame(new_info)
    
    site_info = (
        pd.merge(site_info, new_info_df, on="site_id", how="inner")
        .sort_values(by="site_id")
        .reset_index(drop=True)
    )

    note = try_read(ground_path, "Note")

    tabs = [merged, all_output, site_info, note]
    tab_names = ["Raw Data", "Cleaned Data", "Site Info", "Note From Sponsors"]

    try_save_tabs(tabs, tab_names, clean_ground_path)

#all_sites_sheet()
#clean_surface()