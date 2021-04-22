import pandas as pd
import datetime
import time
import json
import os
from installed_clients.WorkspaceClient import Workspace
from sample_uploader.utils.sample_utils import (
    get_sample,
    save_sample,
    compare_samples,
    generate_user_metadata,
    generate_controlled_metadata,
    generate_source_meta,
    update_acls,
    validate_samples
)
from sample_uploader.utils.parsing_utils import upload_key_format
from sample_uploader.utils.mappings import SAMP_SERV_CONFIG
from sample_uploader.utils.misc_utils import get_workspace_user_perms

# These columns should all be in lower case.
REGULATED_COLS = ['name', 'id', 'parent_id']
NOOP_VALS = ['ND', 'nd', 'NA', 'na', 'None', 'n/a', 'N/A', 'Na', 'N/a', '-']


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


def _produce_samples(
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

    def _get_existing_sample(name, kbase_sample_id):
        prev_sample = None
        if kbase_sample_id:
            prev_sample = get_sample({"id": kbase_sample_id}, sample_url, token)

            if name in existing_sample_names and prev_sample['name'] == name:
                # now we check if the sample 'id' and 'name' are the same
                if existing_sample_names[name]['id'] != prev_sample['id']:
                    raise ValueError(f"'kbase_sample_id' and input sample set have different ID's for sample with name \"{name}\"")
            elif name in existing_sample_names and name != prev_sample['name']:
                # not sure if this is an error case
                raise ValueError(f"sample with kbase_sample_id {kbase_sample_id} cannot be renamed "
                                 f"from {prev_sample['name']} to {name}")
        elif name in existing_sample_names:

            prev_sample = get_sample(existing_sample_names[name], sample_url, token)

        return prev_sample

    for idx, row in df.iterrows():
        # set name field (only required field)
        if not row.get('name'):
            raise RuntimeError(f"'name' field required {row.get('name')} evaluates as false - {row.keys()}")
        name = str(row.get('name'))
        if 'name' in cols:
            cols.pop(cols.index('name'))
        # first we check if a 'kbase_sample_id' column is specified
        kbase_sample_id = None
        if row.get('kbase_sample_id'):
            kbase_sample_id = str(row.pop('kbase_sample_id'))
            if 'kbase_sample_id' in cols:
                cols.pop(cols.index('kbase_sample_id'))
        if row.get('parent_id'):
            parent = str(row.pop('parent_id'))
            if 'parent_id' in cols:
                cols.pop(cols.index('parent_id'))
        else:
            parent = None

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
                "id": name,
                "parent": None,
                "type": "BioReplicate",
                "meta_controlled": controlled_metadata,
                "meta_user": user_metadata,
                'source_meta': source_meta
            }],
            'name': name,
        }
        # get existing sample (if exists)
        prev_sample = _get_existing_sample(name, kbase_sample_id)

        if compare_samples(sample, prev_sample):
            if sample.get('name') not in existing_sample_names:
                existing_sample_names[sample['name']] = prev_sample
            continue
        elif name in existing_sample_names:
            existing_sample_names.pop(name)
        # "save_sample_for_later"
        samples.append({
            'sample': sample,
            'prev_sample': prev_sample,
            'name': name,
            'write': row.get('write'),
            'read': row.get('read'),
            'admin': row.get('admin')
        })
    # add the missing samples from existing_sample_names
    return samples, [existing_sample_names[key] for key in existing_sample_names]


def _save_samples(samples, acls, sample_url, token):
    """"""
    saved_samples = []
    for data in samples:
        sample = data['sample']
        prev_sample = data['prev_sample']
        name = data['name']

        # print('-'*80)
        # print('sample to be saved', json.dumps(sample))
        # print('-'*80)
        sample_id, sample_ver = save_sample(sample, sample_url, token, previous_version=prev_sample)

        saved_samples.append({
            "id": sample_id,
            "name": name,
            "version": sample_ver
        })
        # check input for any reason to update access control list
        # should have a "write", "read", "admin" entry
        writer = data.get('write')
        reader = data.get('read')
        admin  = data.get('admin')
        if writer or reader or admin:
            acls["read"] +=  [r for r in reader]
            acls["write"] += [w for w in writer]
            acls["admin"] += [a for a in admin]
        if len(acls["read"]) > 0 or len(acls['write']) > 0 or len(acls['admin']) > 0:
            _ = update_acls(sample_url, sample_id, acls, token)
    return saved_samples


def format_input_file(df, column_mapping, columns_to_input_names, aliases):
    # try to see if there are any aliases for key fields
    map_aliases = {}
    for key, key_aliases in aliases.items():
        key = upload_key_format(key)
        for alias_key in key_aliases:
            alias_key = upload_key_format(alias_key)
            # check if alias_key in columns
            if alias_key in df.columns:
                # make sure that existing
                if key in df.columns:
                    # if key already exists, continue
                    continue
                map_aliases[alias_key] = key
                if alias_key in columns_to_input_names:
                    val = columns_to_input_names.pop(alias_key)
                    columns_to_input_names[key] = val

    if map_aliases:
        df = df.rename(columns=map_aliases)

    if column_mapping:
        df = df.rename(columns=column_mapping)

    for key in column_mapping:
        if key in columns_to_input_names:
            val = columns_to_input_names.pop(key)
            columns_to_input_names[column_mapping[key]] = val

    return df, columns_to_input_names


def import_samples_from_file(
    params,
    sample_url,
    workspace_url,
    username,
    token,
    column_mapping,
    column_groups,
    date_columns,
    column_unit_regex,
    input_sample_set,
    header_row_index,
    aliases
):
    """
    import samples from '.csv' or '.xls' files in SESAR  format
    """
    # verify inputs
    sample_file = validate_params(params)
    ws_name = params.get('workspace_name')
    df = load_file(sample_file, header_row_index, date_columns)
    # change columns to upload format
    # TODO: make sure separate columns are not being renamed to the same thing
    columns_to_input_names = {upload_key_format(c): c for c in df.columns}
    df = df.rename(columns={c: upload_key_format(c) for c in df.columns})
    df.replace({n:None for n in NOOP_VALS}, inplace=True)

    df, columns_to_input_names = format_input_file(df, column_mapping, columns_to_input_names, aliases)

    # if params.get('id_field'):
    #     id_field = upload_key_format(params['id_field'])
    #     if id_field in list(df.columns):
    #         # here we rename whatever the id field was/is to "id"
    #         columns_to_input_names["id"] = columns_to_input_names.pop(id_field)
    #         df.rename(columns={id_field: "id"}, inplace=True)
    #         # remove "id" rename field from column mapping if exists
    #         if column_mapping:
    #             column_mapping = {key: val for key, val in column_mapping.items() if val != "id"}
    #     else:
    #         raise ValueError(f"'{params['id_field']}' is not a column field in the input file.")
    # else:
    #     print(f"No id_field argument present in params, proceeding with defaults.")

    if params['file_format'].lower() in ['sesar', "enigma"]:
        if 'material' in df.columns:
            df.rename(columns={"material": params['file_format'].lower() + ":material"}, inplace=True)
            val = columns_to_input_names.pop("material")
            columns_to_input_names[params['file_format'].lower() + ":material"] = val
    if params['file_format'].lower() == "kbase":
        if 'material' in df.columns:
            df.rename(columns={"material": "sesar:material"}, inplace=True)
            val = columns_to_input_names.pop("material")
            columns_to_input_names["sesar:material"] = val

    acls = {
        "read": [],
        "write": [],
        "admin": [],
        "public_read": -1  # set to false (<0)
    }
    if params.get('share_within_workspace'):
        # query workspace for user permissions.
        acls = get_workspace_user_perms(workspace_url, params.get('workspace_id'), token, username, acls)
    groups = SAMP_SERV_CONFIG['validators']

    cols = list(set(df.columns) - set(REGULATED_COLS))
    samples, existing_samples = _produce_samples(
        df,
        cols,
        column_groups,
        column_unit_regex,
        sample_url,
        token,
        input_sample_set['samples'],
        columns_to_input_names
    )
    errors = {}
    if params.get('prevalidate'):
        errors = validate_samples([s['sample'] for s in samples], sample_url, token)
    if errors:
        saved_samples = []
    else:
        saved_samples = _save_samples(samples, acls, sample_url, token)
        saved_samples += existing_samples
    return {
        "samples": saved_samples,
        "description": params.get('description')
    }, errors
