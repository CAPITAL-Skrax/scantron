#!/usr/bin/env python
"""Takes a masscan .json file and converts it to a .csv.  In this script, the results are dumped to a directory that
is monitored by a big data analytics agent."""
# Standard Python libraries.
# import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys

# Third party Python libraries.


# Custom Python libraries.


# Scan result with a banner.
"""
{
    "ip": "192.168.1.100",
    "timestamp": "1535461676",
    "ports": [
        {
            "port": 443,
            "proto": "tcp",
            "service": {
                "name": "X509",
                "banner": "MIIFfzCCBGegAw...."
            }
        }
    ]
}
"""

# Scan result without a banner.
"""
{
    "ip": "192.168.1.101",
    "timestamp": "1535461674",
    "ports": [
        {
            "port": 80,
            "proto": "tcp",
            "status": "open",
            "reason": "syn-ack",
            "ttl": 61
        }
    ]
}
"""
# Used when the .json file is 0 bytes and the column names from result_dict cannot be extracted.
CSV_FIELD_NAMES = [
    "starttime",
    "endtime",
    "siteName",
    "scanner",
    "dest_ip",
    "transport",
    "dest_port",
    "app",
    "service",
    "state",
]


def write_results_to_csv_file(results_list, masscan_csv_file_name):
    """Writes results to a .csv file.  Attempts to extract column names, falls back to CSV_FIELD_NAMES."""

    print(f"Writing results to: {masscan_csv_file_name}")

    with open(masscan_csv_file_name, "w") as csvfile:
        try:
            field_names = results_list[0].keys()
        except IndexError:
            field_names = CSV_FIELD_NAMES

        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()

        for result in results_list:
            writer.writerow(result)

    print(f"Done writing results to: {masscan_csv_file_name}")


def main():

    root_dir = "/home/scantron/console"

    # Build directory paths.
    complete_dir = os.path.join(root_dir, "scan_results", "complete")
    processed_dir = os.path.join(root_dir, "scan_results", "processed")
    bigdata_analytics_dir = os.path.join(root_dir, "for_bigdata_analytics")

    # Grab a list of json files from the "complete" folder.
    json_scans = glob.glob(os.path.join(complete_dir, "*.json"))

    # Loop through all valid .json files and export them to .csv files.
    # Then move them to the "processed" directory.
    for scan in json_scans:

        try:
            # Variables used for every file.
            base_scan_file_name = os.path.basename(scan).split(".json")[0]
            masscan_csv_file_name = f"{base_scan_file_name}.csv"
            results_list = []

            if os.path.getsize(scan) == 0:
                print(f"File is 0 bytes: {scan}")

            else:
                # "scan" variable is constructed as "result_file_base_name" in console/scan_scheduler.py
                scan_file_name = os.path.basename(scan)
                site_name = scan_file_name.split("__")[0]

                with open(scan, "r") as fh:

                    # Load json file into memory.  Be sure you have enough.
                    scan_results = json.load(fh)

                    for result in scan_results:

                        try:
                            for port in result["ports"]:

                                # Conforming key values to what big data analytics platform is expecting with
                                # scantron/console/scan_results/nmap_to_csv.py
                                result_dict = {
                                    "starttime": result["timestamp"],
                                    "endtime": result["timestamp"],
                                    "siteName": site_name.lower(),
                                    "scanner": "masscan",
                                    "dest_ip": result["ip"],
                                    "transport": port["proto"],
                                    "dest_port": port["port"],
                                    "app": "",  # Populated below.
                                    "service": "",  # Populated below.
                                    "state": "open",  # Hardcode; "status" key isn't always available with banners.
                                }

                                if "service" in port:
                                    # Shorten SSL/TLS certificates.
                                    if port["service"]["banner"].startswith("MII"):
                                        result_dict["service"] = "custom_service_modification_TLS_cert"

                                    # Shorten source HTML source code pages.
                                    elif re.search(r"\u003c", port["service"]["banner"]):
                                        result_dict["service"] = "custom_service_modification_html_source_blob"

                                    else:
                                        # Replace newlines and carriage returns with spaces.
                                        result_dict["service"] = (
                                            port["service"]["banner"].replace("\n", " ").replace("\r", " ")
                                        )

                                    result_dict["app"] = port["service"]["name"]

                                # We care about all open ports found, not just ones with a banner.
                                results_list.append(result_dict)

                        except Exception as e:
                            print(f"Issue with parsing scan: {result}.  Exception: {e}")
                            sys.exit(0)

            # Pass results and full file path to "for_bigdata_analytics" directory.
            write_results_to_csv_file(results_list, os.path.join(bigdata_analytics_dir, masscan_csv_file_name))

            # csv files have been created, move all .json scan file types from "completed" to "processed" folder.
            # move(source, destination)
            try:
                shutil.move(scan, processed_dir)
            except shutil.Error:
                os.remove(os.path.join(processed_dir, os.path.basename(scan)))
                shutil.move(scan, processed_dir)

        except Exception as e:
            print(f"Exception: {e}")


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Convert a masscan json result file to csv.")
    # parser.add_argument("-f", dest="json_file", action="store", required=True, help="masscan .json file.")
    # parser.add_argument(
    #     "-i", dest="site_name", action="store", required=True, help="Site name: masscan_office or masscan_customer."
    # )
    # parser.add_argument(
    #     "-s", dest="scanner_name", action="store", required=True, help="Scanner name: office, customer, cloud, etc."
    # )

    # args = parser.parse_args()

    # json_file = args.json_file

    # if not os.path.exists(json_file):
    #     print(f"File does not exist: {json_file}")
    #     sys.exit(1)

    # main(**vars(args))
    main()
