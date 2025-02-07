import os

from utils import config


def load_data(path):
    is_header = True
    array = []
    extended_trace = []

    with open(path, "r") as f:
        for line in f:
            if is_header:
                is_header = False
                continue

            t = line.split(",")
            array.append(int(t[1]))

            time_tick_multiple = int(60 / config.time_tick_in_seconds)
            extended_trace.extend(
                [round(int(t[1]) / time_tick_multiple, 2)] * time_tick_multiple
            )


def load_workload_from_dir(workload_dir: str):
    for root, _, files in os.walk("workloads/" + workload_dir):
        for file_name in files:
            if file_name == "cleaned.csv":
                full_path = os.path.join(root, file_name)
                load_data(full_path)
