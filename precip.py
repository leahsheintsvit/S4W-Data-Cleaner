import pandas as pd
import datetime as dt
from pathlib import Path
import pathlib
from lxml import html
import os
import sys

dir = pathlib.Path().resolve()
cleaned_folder = dir / Path("Cleaned Data")
precip_cleaned_path = cleaned_folder / Path("precip-9-9-2026-cleaned.csv")
site_summaries_path = cleaned_folder / Path("precip_ssite_summaries.csv")

precip_data = pd.read_csv(precip_cleaned_path, low_memory = False)

precip_data["year"] = pd.to_datetime(precip_data["msmt_datetime"]).dt.year
precip_data["month"] = pd.to_datetime(precip_data["msmt_datetime"]).dt.month

# maximum_coord_change = 0.00045 # approx 50 meters
all_site_summaries = pd.DataFrame()
sites = precip_data["AutoSiteID"].unique()

for site in sites:
    site_entries = precip_data[[precip_data["AutoSiteID"] == site]]

    site_entries.sort_values(by='msmt_datetime', ascending=False)

    if len(site_entries) < 2:
        continue

    site_summary = (
        site_entries[["year", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month"], ascending = True)
        .reset_index(drop=True)
    )

    site_summary["total_precip_mm"] = 0.0
    site_summary["days_measured"] = 0
    site_summary["mean_daily_precip_mm"] = 0.0
    site_summary["observations"] = 0
    site_summary.insert(0, "AutoSiteID", site)

    for _, entry in site_entries.iterrow():
        index = entry["index"]

        if (index == 0):
            continue
        
        year = entry["year"]
        month = entry["month"]
        precip_mm = entry["precip_mm"]

        filter = (
            (site_summary["year"] == year) &
            (site_summary["month"] == month)
        )

        # total number of days in the month
        total_days = calendar.monthrange(year, month)[1]

        # Get previous measurement date
        cur_date = pd.to_datetime(entry["msmt_datetime"])
        prev_date = pd.to_datetime(site_entries[site_entries["index"] == index - 1]["msmt_datetime"])

        # days (float) since last measurement
        days_since_last = (msmt_date - prev_date).total_seconds() / 86400

        # Do not read measurements that are further than a month apart
        if days_since_last > total_days:
            continue

        # average daily precipitation (mm) since last measurement
        avg_daily_precip = precip_mm / days_since_last

        # days within this month
        days_measured_this_month = (max(prev_date, date(year, month, 1)) - msmt_date).total_seconds / 86400
        
        site_summary[filter]["total_precip_mm"] += avg_daily_precip * days_measured_this_month
        site_summary[filter]["days_measured"] += days_measured_this_month
        site_summary[filter]["observations"] += 1

        # If the measurement bleeds into last month, adjust last month's summary
        if (days_since_last > days_measured_this_month):
            days_last_month = days_since_last - days_measured_this_month

            last_month = (month + 10) % 12 + 1
            last_year = year - 1 if last_month > month else year

            last_filter = (
                (site_summary["year"] == last_year) &
                (site_summary["month"] == last_month)
            )

            site_summary[last_filter]["total_precip_mm"] += avg_daily_precip * days_last_month
            site_summary[last_filter]["days_measured"] += days_last_month
            site_summary[last_filter]["observations"] += 1
        
    daily_avg_precip = site_summary[last_filter]["total_precip_mm"] / site_summary[last_filter]["days_measured"]
    site_summary[last_filter]["mean_daily_precip_mm"] = daily_avg_precip

    all_site_summaries = pd.concat([all_site_summaries, site_summary], ignore_index = True)
    all_site_summaries.sort_values(by = ["year", "month"])
        

        
# PROBLEMS!!!!: 
# 1.) Site IDs do not stay in the same coordinate position; Not good for small-region measurements
# 2.) Measurements are not consistent. Assume the meter is emptied every time, and left to collect until the next measurement.
