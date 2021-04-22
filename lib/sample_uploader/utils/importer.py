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
    update_acls,
    validate_samples
)
from sample_uploader.utils.parsing_utils import upload_key_format
from sample_uploader.utils.mappings import SAMP_SERV_CONFIG
from sample_uploader.utils.misc_utils import get_workspace_user_perms
from sample_uploader.utils.samples_content_error import SampleContentError

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
    if params.get('id_field'):
        try: 
            upload_key_format(params.get('id_field'))
        except SampleContentError as e:
            raise ValueError("Invalid ID field in params: {e.message}")
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
        df = pd.read_csv(sample_file, sep="\t", header=header_row_index, skip_blank_lines=False)
    elif sample_file.endswith('.csv'):
        # df = pd.read_csv(sample_file, parse_dates=date_columns, header=header_row_index)
        df = pd.read_csv(sample_file, header=header_row_index, skip_blank_lines=False)
    elif sample_file.endswith('.xls') or sample_file.endswith('.xlsx'):
        df = pd.read_excel(sample_file, header=header_row_index, skip_blank_lines=False)
    else:
        raise ValueError(f"File {os.path.basename(sample_file)} is not in "
                         f"an accepted file format, accepted file formats "
                         f"are '.xls' '.csv' '.tsv' or '.xlsx'")
    df.dropna(how='all', inplace=True)
    return df


def _produce_samples(
    df,
    cols,
    column_groups,
    column_unit_regex,
    sample_url,
    token,
    existing_samples,
    columns_to_input_names,
    header_row_index
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
                    raise SampleContentError(
                        f"'kbase_sample_id' and input sample set have different ID's for sample with name \"{name}\"",
                        key="id",
                        sample_name=name
                    )
            elif name in existing_sample_names and name != prev_sample['name']:
                # not sure if this is an error case
                raise SampleContentError(
                    f"Cannot rename existing sample from {prev_sample['name']} to {name}",
                    key="id",
                    sample_name=name
                )
        elif name in existing_sample_names:
            prev_sample = get_sample(existing_sample_names[name], sample_url, token)

        return prev_sample

    errors = []
    for idx, row in df.iterrows():
        try:
            if not row.get('id'):
                raise SampleContentError(
                    f"Bad sample ID \"{row.get('id')}\" evaluates as false",
                    key='id',
                    sample_name=row.get('name')
                )
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
        except SampleContentError as e:
            e.row = header_row_index + 1 + idx
            errors.append(e)
    # add the missing samples from existing_sample_names
    return samples, [existing_sample_names[key] for key in existing_sample_names], errors


def _save_samples(samples, acls, sample_url, token):
    """"""
    saved_samples = []
    for data in samples:
        sample = data['sample']
        prev_sample = data['prev_sample']
        name = data['name']

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

    errors = []
    # change columns to upload format
    columns_to_input_names = {}
    for col_idx, col_name in enumerate(df.columns):
        try:
            renamed = upload_key_format(col_name)
            if renamed in columns_to_input_names:
                raise SampleContentError(
                    (f"Duplicate column \"{renamed}\". \"{col_name}\" would overwrite a different column \"{columns_to_input_names[renamed]}\". "
                    "Rename your columns to be unique alphanumericaly, ignoring whitespace and case."), 
                    key=col_name
                )
            columns_to_input_names[renamed] = col_name
        except SampleContentError as e:
            e.column = col_idx
            errors.append(e)

    df = df.rename(columns={columns_to_input_names[col]: col for col in columns_to_input_names})
    df.replace({n:None for n in NOOP_VALS}, inplace=True)

    #TODO: Make sure to check all possible ID fields, even when not parameterized
    if params.get('id_field'):
        id_field = upload_key_format(params.get('id_field'))
        if id_field not in list(df.columns):
            raise ValueError(
                f"The expected ID field column \"{id_field}\" could not be found. "
                "Adjust your parameters or input such that the following are correct:\n"
                f"- File Format: {params.get('file_format')} (the format to which your sample data conforms)\n"
                f"- ID Field: {params.get('id_field','id')}\n (the header of the column containing your IDs)\n"
                f"- Headers Row: {params.get('header_row_index')} (the row # where column headers are located in your spreadsheet)"
            )
        # here we rename whatever the id field was/is to "id"
        columns_to_input_names["id"] = columns_to_input_names.pop(id_field)
        df.rename(columns={id_field: "id"}, inplace=True)
        # remove "id" rename field from column mapping if exists
        if column_mapping:
            column_mapping = {key: val for key, val in column_mapping.items() if val != "id"}

    if not errors:
        if column_mapping:
            df = df.rename(columns=column_mapping)
        # redundant, even harmful if things get out of sync
        # verify_columns(df)
        for key in column_mapping:
            if key in columns_to_input_names:
                val = columns_to_input_names.pop(key)
                columns_to_input_names[column_mapping[key]] = val

        if params['file_format'].upper() in ['SESAR', "ENIGMA"]:
            if 'material' in df.columns:
                df.rename(columns={"material": params['file_format'].upper() + ":material"}, inplace=True)
                val = columns_to_input_names.pop("material")
                columns_to_input_names[params['file_format'].upper() + ":material"] = val
        if params['file_format'].upper() == "KBASE":
            if 'material' in df.columns:
                df.rename(columns={"material": "SESAR:material"}, inplace=True)
                val = columns_to_input_names.pop("material")
                columns_to_input_names["SESAR:material"] = val

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
        sample_url = get_sample_service_url(sw_url)
        samples, existing_samples, produce_errors = _produce_samples(
            df,
            cols,
            column_groups,
            column_unit_regex,
            sample_url,
            token,
            input_sample_set['samples'],
            columns_to_input_names,
            header_row_index
        )
        errors += produce_errors
    
    if params.get('prevalidate') and not errors:
        error_detail = validate_samples([s['sample'] for s in samples], sample_url, token)
        errors += [ SampleContentError(
                e['message'],
                sample_name=e['sample_name'], 
                node=e['node'], 
                key=e['key']
            ) for e in error_detail ]

    if errors:
        saved_samples = []
        # Fill in missing location information for SamplesContentError(s)
        err_col_keys = {}
        err_key_indices = {}
        for col_idx, col_name in enumerate(df.columns):
            err_col_keys[col_idx] = col_name
            err_key_indices[col_name] = col_idx
            if col_name in columns_to_input_names and columns_to_input_names[col_name] != col_name:
                err_key_indices[columns_to_input_names[col_name]] = col_idx

        err_row_sample_names = {}
        err_sample_name_indices = {}
        for row_idx, row in df.iterrows():
            row_pos = header_row_index + 1 + row_idx
            sample_name = row.get('id')
            err_sample_name_indices[sample_name] = row_pos
            err_row_sample_names[row_pos] = sample_name

        for e in errors:
            if e.column!=None and e.key==None and e.column in err_col_keys:
                e.key = err_col_keys[e.column]
            if e.column==None and e.key!=None and e.key in err_key_indices:
                e.column = err_key_indices[e.key]
            if e.row!=None and e.sample_name==None and e.row in err_row_sample_names:
                e.sample_name = err_row_sample_names[e.row]
            if e.row==None and e.sample_name!=None and e.sample_name in err_sample_name_indices:
                e.row = err_sample_name_indices[e.sample_name]
    else:
        saved_samples = _save_samples(samples, acls, sample_url, token)
        saved_samples += existing_samples

    return {
        "samples": saved_samples,
        "description": params.get('description')
    }, errors
