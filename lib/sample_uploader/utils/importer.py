import pandas as pd
import datetime
import time
import json
import os
from installed_clients.WorkspaceClient import Workspace
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
from sample_uploader.utils.mappings import SAMP_SERV_CONFIG

# These columns should all be in lower case.
REGULATED_COLS = ['name', 'id', 'parent_id']
NOOP_VALS = ['ND', 'nd', 'NA', 'na', 'None', 'n/a', 'N/A', 'Na', 'N/a']


VALIDATORS = SAMP_SERV_CONFIG['validators']

def verify_columns(df):
    """"""
    cols = df.columns
    for col in cols:
        if VALIDATORS.get(col):
            args = VALIDATORS.get(col)
            for val in args.get('validators'):
                func_str = val.get('callable_builder', '')
                params = val.get('parameters')
                func = verifiers.get(func_str)
                # only verify if local function exists
                if func:
                    try:
                        func(df[col], params)
                    except Exception as err:
                        raise ValueError(f"error parsing column \"{col}\" ")


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
    header_row_index,
    date_columns
):
    """"""
    if sample_file.endswith('.tsv'):
        # df = pd.read_csv(sample_file, sep="\t", parse_dates=date_columns, header=header_row_index)
        df = pd.read_csv(sample_file, sep="\t", header=header_row_index)
    elif sample_file.endswith('.csv'):
        # df = pd.read_csv(sample_file, parse_dates=date_columns, header=header_row_index)
        df = pd.read_csv(sample_file, header=header_row_index)
    elif sample_file.endswith('.xls') or sample_file.endswith('.xlsx'):
        df = pd.read_excel(sample_file, header=header_row_index)
    else:
        raise ValueError(f"File {os.path.basename(sample_file)} is not in "
                         f"an accepted file format, accepted file formats "
                         f"are '.xls' '.csv' '.tsv' or '.xlsx'")
    return df


def _get_workspace_user_perms(workspace_url, workspace_id, token, username, acls):
    """
    """
    ws_client = Workspace(workspace_url, token=token)
    results = ws_client.get_permissions_mass({'workspaces': [{'id': workspace_id}]}) 
    for user in results['perms'][0]:
        # skip owner of the samples.
        if user == username:
            continue
        if results['perms'][0][user] == 'a':
            acls['admin'].append(user)
        if results['perms'][0][user] == 'r':
            acls['read'].append(user)
        if results['perms'][0][user] == 'w':
            acls['write'].append(user)
        if results['perms'][0][user] == 'n':
            continue
    return acls

def produce_samples(
    df,
    cols,
    column_groups,
    column_unit_regex,
    sample_url,
    token,
    existing_samples,
    columns_to_input_names,
    acls
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
            user_metadata = generate_user_metadata(
                row,
                cols,
                column_groups,
                column_unit_regex
            )
            source_meta = generate_source_meta(
                row,
                controlled_metadata.keys(),
                columns_to_input_names
            )

            sample = {
                'node_tree': [{
                    "id": str(row['id']),
                    "parent": None,
                    "type": "BioReplicate",
                    "meta_controlled": controlled_metadata,
                    "meta_user": user_metadata,
                    'source_meta': source_meta
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
            # should have a "write", "read", "admin" entry
            writer = row.get('write')
            reader = row.get('read')
            admin  = row.get('admin')
            if writer or reader or admin:
                acls["read"] +=  [r for r in reader]
                acls["write"] += [w for w in writer]
                acls["admin"] += [a for a in admin]
            if len(acls["read"]) > 0 or len(acls['write']) > 0 or len(acls['admin']) > 0:
                resp = update_acls(sample_url, sample_id, acls, token)
        else:
            raise RuntimeError(f"{row.get('id')} evaluates as false - {row.keys()}")
    # add the missing samples from existing_sample_names
    samples += [existing_sample_names[key] for key in existing_sample_names]
    return samples


def import_samples_from_file(
    params,
    sw_url,
    workspace_url,
    username,
    token,
    column_mapping,
    column_groups,
    date_columns,
    column_unit_regex,
    input_sample_set,
    header_row_index
):
    """
    import samples from '.csv' or '.xls' files in SESAR  format
    """
    # verify inputs
    sample_file = validate_params(params)
    ws_name = params.get('workspace_name')
    df = load_file(sample_file, header_row_index, date_columns)
    # change columns to upload format
    columns_to_input_names = {upload_key_format(c): c for c in df.columns}
    df = df.rename(columns={c: upload_key_format(c) for c in df.columns})
    df.replace({n:None for n in NOOP_VALS}, inplace=True)

    if params.get('id_field'):
        id_field = upload_key_format(params['id_field'])
        if id_field in list(df.columns):
            # here we rename whatever the id field was/is to "id"
            columns_to_input_names["id"] = columns_to_input_names.pop(id_field)
            df.rename(columns={id_field: "id"}, inplace=True)
            # remove "id" rename field from column mapping if exists
            if column_mapping:
                column_mapping = {key: val for key, val in column_mapping.items() if val != "id"}
        else:
            raise ValueError(f"'{params['id_field']}' is not a column field in the input file.")
    else:
        print(f"{params.get('id_field')} evaluates as false. No id_field argument present in params")

    if column_mapping:
        df = df.rename(columns=column_mapping)
    verify_columns(df)
    for key in column_mapping:
        if key in columns_to_input_names:
            val = columns_to_input_names.pop(key)
            columns_to_input_names[column_mapping[key]] = val

    if params['file_format'].upper() in ['SESAR', "ENIGMA"]:
        if 'material' in df.columns:
            df.rename({"material": params['file_format'].upper() + ":material"}, inplace=True)
    if params['file_format'].upper() == "KBASE":
        if 'material' in df.columns:
            df.rename({"material": "SESAR:material"}, inplace=True)

    acls = {
        "read": [],
        "write": [],
        "admin": []
    }
    if params.get('share_within_workspace'):
        # query workspace for user permissions.
        acls = _get_workspace_user_perms(workspace_url, params.get('workspace_id'), token, username, acls)
    groups = SAMP_SERV_CONFIG['validators']

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
        columns_to_input_names,
        acls
    )
    return {
        "samples": samples,
        "description": params.get('description')
    }
