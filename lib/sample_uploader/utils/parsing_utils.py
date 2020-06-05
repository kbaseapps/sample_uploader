# utilities for parsing data.
import pandas as pd


def upload_key_format(key):
    return "_".join(key.strip().lower().replace("(", "").replace(")", "").replace("/", "_").split())


def check_value_in_list(val, array, return_idx=False):
    # this function checks if item is in list like object
    # with no case sensitivity.
    if return_idx:
        for idx, a in enumerate(array):
            if str(val).strip().lower() == str(a).strip().lower(): return idx
        return None
    else:
        return str(val).strip().lower() in [str(a).strip().lower() for a in array]

def parse_grouped_data(row, group):
    mtd = {}
    used_cols = set([])
    for val in group:
        # if starts with 'str:', not a column
        if group[val].startswith('str:'):
            mtd[val] = group[val][4:]
        # default behaviour expects a column as the value
        else:
            # check if the column is in the data and is not null
            if group[val] in row and not pd.isnull(row[group[val]]):
                try:
                    mtd_val = float(row[group[val]])
                except (ValueError, TypeError):
                    mtd_val = row[group[val]]
                mtd[val] = mtd_val
                used_cols.add(group[val])
    return mtd, used_cols


def handle_groups_metadata(row, cols, groups):
    metadata = {}
    used_cols = set([])
    for group in groups:
        if group['value'] not in cols:
            continue
        mtd, curr_used_cols = parse_grouped_data(row, group)
        used_cols = used_cols | curr_used_cols
        metadata[group["value"]] = mtd
    return metadata, used_cols
