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


def validate_params(params):
    if not params.get('sample_file'):
        raise ValueError(f"sample_file argument required in params: {params}")
    if not params.get('workspace_name'):
        raise ValueError(f"workspace_name argument required in params: {params}")
    sample_file = params.get('sample_file')
    if not os.path.isfile(sample_file):
        # try prepending '/staging/' to file and check then
        if os.path.isfile(os.path.join('/staging', sample_file)):
            sample_file = os.path.join('/staging', sample_file)
        else:
            raise ValueError(f"input file {sample_file} does not exist.")
    ws_name = params.get('workspace_name')
    return sample_file


def load_file(sample_file, header_index, date_columns):
    """"""
    if sample_file.endswith('.tsv'):
        df = pd.read_csv(sample_file, sep="\t", parse_dates=date_columns, header=header_index)
    elif sample_file.endswith('.csv'):
        df = pd.read_csv(sample_file, parse_dates=date_columns, header=header_index)
    elif sample_file.endswith('.xls') or sample_file.endswith('.xlsx'):
        df = pd.read_excel(sample_file, header=header_index)
    else:
        raise ValueError(f"File {os.path.basename(sample_file)} is not in an accepted file format, "
                         f"accepted file formats are '.xls' '.csv' '.tsv' or '.xlsx'")
    return df


def produce_samples(df, cols, column_groups, column_unit_regex, sample_url, token):
    """
    """
    samples = []
    for idx, row in df.iterrows():
        if row['id']:
            # use name field as name, if there is non-reuse id.
            if row.get('name'):
                name = str(row['name'])
            else:
                name = str(row['id'])
            parent = str(row['parent_id'])
            sample = {
                'node_tree': [{
                    "id": str(row['id']),
                    "parent": None,
                    "type": "BioReplicate",
                    "meta_controlled": {},
                    "meta_user": generate_metadata(
                        row,
                        cols,
                        column_groups,
                        column_unit_regex
                    )
                }],
                'name': name,
            }
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
    return samples


def import_samples_from_file(
    params,
    sw_url,
    token,
    column_verification_map,
    column_mapping,
    column_groups,
    date_columns,
    column_unit_regex,
    header_index
):
    """
    import samples from '.csv' or '.xls' files in SESAR  format
    """
    # verify inputs
    sample_file = validate_params(params)
    ws_name = params.get('workspace_name')
    df = load_file(sample_file, header_index, date_columns)
    verify_columns(df, column_verification_map)
    df = df.rename(columns=column_mapping)
    cols = df.columns
    cols = list(set(cols) - set(REGULATED_COLS))
    # process and save samples
    sample_url = get_sample_service_url(sw_url)
    samples = produce_samples(
        df,
        cols,
        column_groups,
        column_unit_regex,
        sample_url,
        token
    )

    return {
        "samples": samples,
        "description": params.get('description')
    }
