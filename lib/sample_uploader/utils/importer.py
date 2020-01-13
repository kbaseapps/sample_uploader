import pandas as pd
import datetime
import time
import json
import os
from .sample_utils import get_sample_service_url, save_sample, generate_metadata, update_acls

REGULATED_COLS = ['name', 'id', 'parent_id']


def verify_columns(df, column_verification_map):
    """"""
    cols = df.columns
    for col in cols:
        func, args = column_verification_map.get(col)
        try:
            func(df[col], *args)
        except Exception as err:
            raise ValueError(f"error parsing column \"{col}\" - {err}")


def import_samples_from_file(params, sw_url, token, column_verification_map, column_mapping, column_groups):
    """
    import samples from '.csv' or '.xls' files in SESAR format    """
    # verify inputs
    if not params.get('sample_file'):
        raise ValueError(f"sample_file argument required in params: {params}")
    if not params.get('workspace_name'):
        raise ValueError(f"workspace_name argument required in params: {params}")
    sample_file = params.get('sample_file')
    # make sure that sample file exists,
    if not os.path.isfile(sample_file):
        # try prepending '/staging/' to file and check then
        if os.path.isfile(os.path.join('/staging', sample_file)):
            sample_file = os.path.join('/staging', sample_file)
        else:
            raise ValueError(f"input file {sample_file} does not exist.")
    ws_name = params.get('workspace_name')

    if sample_file.endswith('.csv') or sample_file.endswith('.tsv'):
        df = pd.read_csv(sample_file, parse_dates=["Release Date", "Collection date"], header=1)
    elif sample_file.endswith('.xls'):
        df = pd.read_excel(sample_file, header=1)
    verify_columns(df, column_verification_map)
    df = df.rename(columns=column_mapping)
    cols = df.columns
    cols = list(set(cols) - set(REGULATED_COLS))
    # process and save samples
    sample_url = get_sample_service_url(sw_url)

    samples = []
    for idx, row in df.iterrows():
        if row['id']:
            name  = str(row['name'])
            sample = {
                'node_tree': [{
                    "id": str(row['id']),
                    "parent": None,
                    "type": "BioReplicate",
                    "meta_controlled": {},
                    "meta_user": generate_metadata(row, cols, column_groups)
                }],
                'name': name,
            }
            # print(json.dumps(sample, indent=2, default=str), ',')
            sample_id = save_sample(sample, sample_url, token)
            samples.append({
                "id": sample_id,
                "name": name
            })
            # check input for any reason to update access control list
            # should have a "writer", "reader", "admin" entry
            writer = row.get('writer')
            reader = row.get('reader')
            admin  = row.get('admin')
            if writer or reader or admin:
                acls = {
                    "reader": [r for r in reader],
                    "writer": [w for w in writer],
                    "admin": [a for a in admin]
                }
                update_acls(sample_url, sample_id, acls)
        else:
            raise RuntimeError(f"{row['id']} evaluates as false")
    return {
        "samples": samples,
        "description": params.get('description')
    }
