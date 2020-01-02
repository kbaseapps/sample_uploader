import pandas as pd
import datetime
import time
import json
from .sample_utils import get_sample_service_url, save_sample, generate_metadata

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

    sample_ids = []
    for idx, row in df.iterrows():
        if row['id']:
            sample = {
                'node_tree': [{
                    "id": str(row['id']),
                    "parent": None,
                    "type": "BioReplicate",
                    "meta_controlled": {},
                    "meta_user": generate_metadata(row, cols, column_groups)
                }],
                'name': str(row['name']),
            }
            # print(json.dumps(sample, indent=2, default=str), ',')
            sample_ids.append(save_sample(sample, sample_url, token))
        else:
            raise RuntimeError(f"{row['id']} evaluates as false")
    return {
        "sample_ids": sample_ids
    }
