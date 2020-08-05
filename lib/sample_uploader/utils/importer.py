import pandas as pd
import datetime
import time
import json
import os
from sample_uploader.utils.sample_utils import (
    get_sample_service_url,
    get_sample,
    save_sample,
    compare_samples,
    generate_user_metadata,
    generate_controlled_metadata,
    generate_source_meta,
    update_acls
)
from sample_uploader.utils.verifiers import verifiers
from sample_uploader.utils.parsing_utils import upload_key_format
# from sample_uploader.utils.mappings import shared_fields

# These columns should all be in lower case.
REGULATED_COLS = ['name', 'id', 'parent_id']
NOOP_VALS = ['ND', 'nd', 'NA', 'na', 'None', 'n/a', 'N/A']


def verify_columns(
    df,
    column_verification_map
):
    """"""
    cols = df.columns
    for col in cols:
        if column_verification_map.get(col):
            func_str, args = column_verification_map.get(col)
            func = verifiers.get(func_str)
            if not func:
                raise ValueError(f"no such verifying function {func_str}")
            try:
                func(df[col], *args)
            except Exception as err:
                raise ValueError(f"error parsing column \"{col}\" - {err}")
        # else:
        #     raise ValueError(f"column {col} not supported in input format.")


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


def load_file(
    sample_file,
    header_index,
    date_columns
):
    """"""
    # def find_date_cols(sample_file, date_columns, sep=','):
    #     with open(sample_file) as f:
    #         for i in range(header_index + 1):
    #             col_line = f.readline()
    #     cols = [c.lower() for c in col_line.split(sep)]
    #     new_dcs = []
    #     for dc in date_columns:
    #         if dc.lower() in cols:
    #             new_dcs.append(dc)
    #     return new_dcs
    if sample_file.endswith('.tsv'):
        # df = pd.read_csv(sample_file, sep="\t", parse_dates=date_columns, header=header_index)
        df = pd.read_csv(sample_file, sep="\t", header=header_index)
    elif sample_file.endswith('.csv'):
        # df = pd.read_csv(sample_file, parse_dates=date_columns, header=header_index)
        df = pd.read_csv(sample_file, header=header_index)
    elif sample_file.endswith('.xls') or sample_file.endswith('.xlsx'):
        df = pd.read_excel(sample_file, header=header_index)
    else:
        raise ValueError(f"File {os.path.basename(sample_file)} is not in "
                         f"an accepted file format, accepted file formats "
                         f"are '.xls' '.csv' '.tsv' or '.xlsx'")
    return df


def produce_samples(
    df,
    cols,
    column_groups,
    column_unit_regex,
    sample_url,
    token,
    existing_samples,
    columns_to_input_names
):
    """"""
    samples = []
    existing_sample_names = {sample['name']: sample for sample in existing_samples}

    for idx, row in df.iterrows():
        if row.get('id'):
            # first we check if a 'kbase_sample_id' column is specified
            kbase_sample_id = None
            if row.get('kbase_sample_id'):
                kbase_sample_id = str(row.pop('kbase_sample_id'))
                if 'kbase_sample_id' in cols:
                    cols.pop(cols.index('kbase_sample_id'))
            # use name field as name, if there is non-reuse id.
            if row.get('name'):
                name = str(row['name'])
            else:
                name = str(row['id'])
            if row.get('parent_id'):
                parent = str(row.pop('parent_id'))
                if 'parent_id' in cols:
                    cols.pop(cols.index('parent_id'))
            if 'id' in cols:
                cols.pop(cols.index('id'))
            if 'name' in cols:
                cols.pop(cols.index('name'))

            controlled_metadata = generate_controlled_metadata(
                row,
                column_groups
            )
            sample = {
                'node_tree': [{
                    "id": str(row['id']),
                    "parent": None,
                    "type": "BioReplicate",
                    "meta_controlled": controlled_metadata,
                    "meta_user": generate_user_metadata(
                        row,
                        cols,
                        column_groups,
                        column_unit_regex
                    ),
                    'source_meta': generate_source_meta(
                        row,
                        controlled_metadata.keys(),
                        columns_to_input_names
                    )
                }],
                'name': name,
            }
            prev_sample = None
            if kbase_sample_id:
                prev_sample = get_sample({"id": kbase_sample_id}, sample_url, token)
                if name in existing_sample_names and prev_sample['name'] == name:
                    # now we check if the sample 'id' and 'name' are the same
                    if existing_sample_names[name]['id'] != prev_sample['id']:
                        raise ValueError(f"'kbase_sample_id' and input sample set have different ID's for sample: {name}")
                elif name in existing_sample_names and name != prev_sample['name']:
                    # not sure if this is an error case
                    raise ValueError(f"Cannot rename existing sample from {prev_sample['name']} to {name}")
            elif name in existing_sample_names:
                prev_sample = get_sample(existing_sample_names[name], sample_url, token)
            if compare_samples(sample, prev_sample):
                if sample.get('name') not in existing_sample_names:
                    existing_sample_names[sample['name']] = prev_sample
                continue
            elif name in existing_sample_names:
                existing_sample_names.pop(name)

            sample_id, sample_ver = save_sample(sample, sample_url, token, previous_version=prev_sample)

            samples.append({
                "id": sample_id,
                "name": name,
                "version": sample_ver
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
                update_acls(sample_url, sample_id, acls, token)
        else:
            raise RuntimeError(f"{row['id']} evaluates as false")
    # add the missing samples from existing_sample_names
    samples += [existing_sample_names[key] for key in existing_sample_names]
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
    input_sample_set,
    header_index
):
    """
    import samples from '.csv' or '.xls' files in SESAR  format
    """
    # verify inputs
    sample_file = validate_params(params)
    ws_name = params.get('workspace_name')
    df = load_file(sample_file, header_index, date_columns)
    # change columns to upload format
    columns_to_input_names = {upload_key_format(c): c for c in df.columns}
    df = df.rename(columns={c: upload_key_format(c) for c in df.columns})
    verify_columns(df, column_verification_map)
    df = df.rename(columns=column_mapping)
    for key in column_mapping:
        if key in columns_to_input_names:
            val = columns_to_input_names.pop(key)
            columns_to_input_names[column_mapping[key]] = val
    df.replace({n:None for n in NOOP_VALS}, inplace=True)

    if params['file_format'].upper() in ['SESAR', "ENIGMA"]:
        if 'material' in df.columns:
            df.rename({"material": params['file_format'].upper() + ":material"}, inplace=True)

    # process and save samples
    cols = list(set(df.columns) - set(REGULATED_COLS))
    sample_url = get_sample_service_url(sw_url)
    samples = produce_samples(
        df,
        cols,
        column_groups,
        column_unit_regex,
        sample_url,
        token,
        input_sample_set['samples'],
        columns_to_input_names
    )
    return {
        "samples": samples,
        "description": params.get('description')
    }
