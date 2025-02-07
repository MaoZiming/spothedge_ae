import json
import os

from utils import config

LARGE_VALUE = 1000000000


def load_data(path, region):
    # print(path, region)
    with open(path, "r") as f:
        data_json = json.load(f)
    data = data_json["data"]
    config.gap_seconds = data_json["metadata"]["gap_seconds"]
    if "1-node" in path:
        assert False, "1-node is not used"
    elif "2-month" in path:
        config.trace_for_each_region[region] = [
            LARGE_VALUE if d == 1 else 0 for d in data
        ]
    elif "4" in path:
        config.trace_for_each_region[region] = data
    elif "16" in path:
        config.trace_for_each_region[region] = data
    elif "a100" in path:
        config.trace_for_each_region[region] = data
    else:
        raise NotImplementedError

    expanded_trace = []
    for avail in config.trace_for_each_region[region]:
        expanded_trace.extend(
            [avail] * int(config.gap_seconds / config.time_tick_in_seconds)
        )

    config.trace_for_each_region[region] = expanded_trace
    config.min_trace_len = min(config.min_trace_len, len(expanded_trace))


def load_trace_from_dir(trace_dir: str):
    regions = []
    for root, dirs, files in os.walk("data/" + trace_dir):
        for file_name in files:
            if file_name.endswith(".json"):
                full_path = os.path.join(root, file_name)
                load_data(full_path, file_name)
                regions.append(file_name)
        dirs.clear()  # do not walk sub directories
    config.regions = regions
