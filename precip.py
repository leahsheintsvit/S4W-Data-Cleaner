import pandas as pd
import datetime as dt
from pathlib import Path
import pathlib
from lxml import html
import numpy as np
import calendar
import time
import os
import sys

dir = pathlib.Path().resolve()
cleaned_folder = dir / Path("Cleaned Data")
backup_folder = dir / Path("Backup")

precip_cleaned_path = cleaned_folder / Path("precip-9-9-2026-cleaned.csv")
site_summaries_path = cleaned_folder / Path("precip_site_summaries.csv")
monthly_summaries_path = cleaned_folder / Path("precip_monthly.csv")

def create_site_summaries():
    precip_data = try_read(precip_cleaned_path)

    precip_data["year"] = pd.to_datetime(precip_data["msmt_datetime"]).dt.year
    precip_data["month"] = pd.to_datetime(precip_data["msmt_datetime"]).dt.month

    # maximum_coord_change = 0.00045 # approx 50 meters
    all_site_summaries = pd.DataFrame()
    sites = precip_data["AutoSiteID"].unique()

    i = 0

    for site in sites:
        i += 1

        print(f"Reading Site: {site} ({i}/{len(sites)})")

        site_entries = (
            precip_data[precip_data["AutoSiteID"] == site]
            .drop_duplicates(subset=['msmt_datetime'])
            .sort_values(by='msmt_datetime', ascending=True)
            .reset_index(drop=True)
        )

        site_entries.insert(0, "index", site_entries.index)

        if len(site_entries) < 2:
            continue

        site_summary = (
            site_entries[["year", "month"]]
            .drop_duplicates()
            .sort_values(["year", "month"], ascending = True)
            .reset_index(drop=True)
        )

        site_summary["total_precip_mm"] = 0.0
        site_summary["days_measured"] = 0.0
        site_summary["mean_daily_precip_mm"] = 0.0
        site_summary["observations"] = 0
        site_summary.insert(0, "AutoSiteID", site)

        # record
        # wait 50 days
        # record (discard)
        # record

        for _, entry in site_entries.iterrows():
        
            index = entry["index"]

            if (index == 0):
                continue
            
            year = entry["year"]
            month = entry["month"]
            precip_mm = entry["precip_mm"]
            msmt_date = pd.to_datetime(entry["msmt_datetime"])

            filter = (
                (site_summary["year"] == year) &
                (site_summary["month"] == month)
            )

            # total number of days in the month
            total_days = calendar.monthrange(year, month)[1]

            # Get previous measurement date
            cur_date = pd.to_datetime(entry["msmt_datetime"])
            prev_date = pd.to_datetime(site_entries[site_entries["index"] == index - 1]["msmt_datetime"].iloc[0])

            # days (float) since last measurement
            days_since_last = (msmt_date - prev_date).total_seconds() / 86400

            if (days_since_last == 0):
                print(f"Site {site}, entry {index} has a duplicated date: {cur_date}; {prev_date}")
                sys.exit()

            # Do not read measurements that are further than a month apart
            if days_since_last > total_days:
                continue

            # average daily precipitation (mm) since last measurement
            avg_daily_precip = precip_mm / days_since_last

            month_start = pd.Timestamp(year=year, month=month, day=1)

            # days within this month
            days_measured_this_month = (msmt_date - max(prev_date, month_start)).total_seconds() / 86400
            
            site_summary.loc[filter, "total_precip_mm"] += avg_daily_precip * days_measured_this_month
            site_summary.loc[filter, "days_measured"] += round(days_measured_this_month, 2)
            site_summary.loc[filter, "observations"] += 1

            # If the measurement bleeds into last month, adjust last month's summary
            if (days_since_last > days_measured_this_month):
                days_last_month = days_since_last - days_measured_this_month
                
                last_month = (month + 10) % 12 + 1
                last_year = year - 1 if last_month > month else year

                last_filter = (
                    (site_summary["year"] == last_year) &
                    (site_summary["month"] == last_month)
                )

                site_summary.loc[last_filter, "total_precip_mm"] += avg_daily_precip * days_last_month
                site_summary.loc[last_filter, "days_measured"] += round(days_last_month, 2)
                site_summary.loc[last_filter, "observations"] += 1

        print("\033[F\033[K", end="")

        site_summary = site_summary[site_summary["days_measured"] > 0].reset_index(drop=True)
        all_site_summaries = pd.concat([all_site_summaries, site_summary], ignore_index = True)

    all_site_summaries["mean_daily_precip_mm"] = all_site_summaries["total_precip_mm"] / all_site_summaries["days_measured"]

    all_site_summaries = all_site_summaries.sort_values(by=["year", "month", "AutoSiteID"]).reset_index(drop=True)

    try_save(all_site_summaries, site_summaries_path)

    print(f"Site summaries file created: {site_summaries_path}")

def create_monthly_summaries():

    all_site_summaries = try_read(site_summaries_path)

    unique_year = all_site_summaries["year"].unique()
    unique_month = all_site_summaries["month"].unique()

    all_monthly_summaries = pd.DataFrame()

    for year in unique_year:

        for month in unique_month:

            summaries_in_month = all_site_summaries[(all_site_summaries["year"] == year) & (all_site_summaries["month"] == month)]

            if len(summaries_in_month) == 0:
                continue

            monthly_summary = pd.DataFrame([{
                "year": year,
                "month": month,
                "start_date": pd.Timestamp(year=year, month=month, day=1),
                "total_precip_mm": np.nan,
                "mean_daily_precip_mm": np.nan,
                "total_expected_precip_mm": np.nan,
                "total_sites": len(summaries_in_month),
                "total_observations": 0,
                "days_in_month": calendar.monthrange(year, month)[1]
            }])

            total_days_measured = summaries_in_month["days_measured"].sum()

            if (total_days_measured > 0):
                
                total_precip_mm = summaries_in_month["total_precip_mm"].sum()

                mean_daily_precip_mm = total_precip_mm / total_days_measured

                total_observations = summaries_in_month["observations"].sum()

                monthly_summary.loc[0, "total_precip_mm"] = total_precip_mm
                monthly_summary.loc[0, "total_days_measured"] = total_days_measured
                monthly_summary.loc[0, "mean_daily_precip_mm"] = mean_daily_precip_mm
                monthly_summary.loc[0, "total_observations"] = total_observations

            all_monthly_summaries = pd.concat([all_monthly_summaries, monthly_summary], ignore_index = True)

    all_monthly_summaries["total_expected_precip_mm"] = all_monthly_summaries["mean_daily_precip_mm"] * all_monthly_summaries["days_in_month"]

    all_monthly_summaries = all_monthly_summaries.drop(columns=["days_in_month", "total_precip_mm", "total_days_measured"])

    all_monthly_summaries = all_monthly_summaries.sort_values(by=["start_date"])

    try_save(all_monthly_summaries, monthly_summaries_path)

    print(f"Monthly summaries file created: {monthly_summaries_path}")

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

# PROBLEMS!!!!: 
# 1.) Site IDs do not stay in the same coordinate position; Not good for small-region measurements
# 2.) Measurements are not consistent. Assume the meter is emptied every time, and left to collect until the next measurement.

# Assumtions!!!!:
# 1.) Site IDs are tied to specific bottles at specific positions.
# 2.) The bottle is emptied every time, and left to collect until the next measurement.
# 3.) Measurements that take longer than 1 month are discarded
# 4.) Measurements are all accurate and quality controlled

# create_site_summaries()
create_monthly_summaries()
