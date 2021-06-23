import pandas as pd
import warnings
import os
import copy

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
from sample_uploader.utils.transformations import FieldTransformer
from sample_uploader.utils.parsing_utils import upload_key_format
from sample_uploader.utils.mappings import SAMP_SERV_CONFIG, CORE_FIELDS, NON_PREFIX_TO_PREFIX
from sample_uploader.utils.misc_utils import get_workspace_user_perms
from sample_uploader.utils.samples_content_warning import SampleContentWarning, SampleContentWarningContext

# These columns should all be in lower case.
REQUIRED_COLS = {'name'}
REGULATED_COLS = ['name', 'id', 'parent_id']
NOOP_VALS = ['ND', 'nd', 'NA', 'na', 'None', 'n/a', 'N/A', 'Na', 'N/a', '-']


def find_header_row(sample_file, file_format):
    if not os.path.isfile(sample_file):
        # try prepending '/staging/' to file and check then
        if os.path.isfile(os.path.join('/staging', sample_file)):
            sample_file = os.path.join('/staging', sample_file)
        else:
            raise ValueError(f"input file {sample_file} does not exist.")

    header_row_index = 0
    if file_format.lower() == "sesar":

        if sample_file.endswith('.tsv') or sample_file.endswith('.csv'):
            reader = pd.read_csv(sample_file, sep=None, iterator=True)
            inferred_sep = reader._engine.data.dialect.delimiter
            with open(sample_file) as f:
                first_line = f.readline()
                second_line = f.readline()

            # when an extra header presents,
            # the first line (SESAR header line) should have an unequal number of columns than the second line (the real header line).
            # TODO: this function will fail if the extra header line happens to have exactly the same number of columns as the real header line
            non_empty_header = [i for i in first_line.split(inferred_sep) if i not in ['', '\n']]
            if len(non_empty_header) != len(second_line.split(inferred_sep)):
                header_row_index = 1

        elif sample_file.endswith('.xls') or sample_file.endswith('.xlsx'):
            df = pd.read_excel(sample_file)

            # when an extra header presents,
            # all of the unmatched columns are indexed as 'Unnamed xx'.
            unnamed_cols = [i for i in df.columns if 'Unnamed' in i]
            if len(unnamed_cols) > 0:
                header_row_index = 1
        else:
            raise ValueError(f"File {os.path.basename(sample_file)} is not in "
                             f"an accepted file format, accepted file formats "
                             f"are '.xls' '.csv' '.tsv' or '.xlsx'")

    return header_row_index


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
    if params.get('name_field'):
        try:
            upload_key_format(params.get('name_field'))
        except SampleContentWarning as e:
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
    # Remove empty rows and change index labels to row number
    df.dropna(how='all', inplace=True)
    df.index += header_row_index+1

    # remove duplicate rows to ensure sample set doesn't have identical samples
    df.drop_duplicates(inplace=True)

    return df


def _produce_samples(
    callback_url,
    df,
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

    if not REQUIRED_COLS.issubset(df.columns):
        raise ValueError(
            f'Required "name" column missing from input. Use "name" or '
            f'an alias ("sample name", "sample id", "samplename", "sampleid") '
            f'Existing fields ({df.columns})'
        )

    def _get_existing_sample(name, kbase_sample_id):
        prev_sample = None
        if kbase_sample_id:
            prev_sample = get_sample({"id": kbase_sample_id}, sample_url, token)

            if name in existing_sample_names and prev_sample['name'] == name:
                # now we check if the sample 'id' and 'name' are the same
                if existing_sample_names[name]['id'] != prev_sample['id']:
                    raise SampleContentWarning(
                        f"'kbase_sample_id' and input sample set have different ID's for sample with name \"{name}\"",
                        key="id",
                        sample_name=name
                    )
            elif name in existing_sample_names and name != prev_sample['name']:
                # not sure if this is an error case
                raise SampleContentWarning(
                    f"Cannot rename existing sample from {prev_sample['name']} to {name}",
                    key="id",
                    sample_name=name
                )
        elif name in existing_sample_names:
            existing_sample = copy.deepcopy(existing_sample_names[name])
            # remove version of samples from sample set in order to get the latest version of sample
            existing_sample.pop('version', None)
            prev_sample = get_sample(existing_sample, sample_url, token)

        return prev_sample

    field_transformer = FieldTransformer(callback_url)

    cols = list(set(df.columns) - set(REQUIRED_COLS))
    imported_sample_names = list()
    for row_num, row in df.iterrows():
        try:
            # only required field is 'name'
            if not row.get('name'):
                raise SampleContentWarning(
                    f"Bad sample name \"{row.get('name')}\". Cell content evaluates as false",
                    key='name',
                    sample_name=row.get('name')
                )
            name = str(row.pop('name'))
            if 'name' in cols:
                cols.pop(cols.index('name'))

            # check if a 'kbase_sample_id' column is specified
            kbase_sample_id = None
            if row.get('kbase_sample_id'):
                kbase_sample_id = str(row.pop('kbase_sample_id'))
                if 'kbase_sample_id' in cols:
                    cols.pop(cols.index('kbase_sample_id'))
            if row.get('parent_id'):
                parent = str(row.pop('parent_id'))
                if 'parent_id' in cols:
                    cols.pop(cols.index('parent_id'))

            # tranformations for data in row.
            row = field_transformer.field_transformations(row, cols)

            controlled_metadata, controlled_cols = generate_controlled_metadata(
                row,
                column_groups
            )
            # remove controlled columns from cols.
            user_metadata = generate_user_metadata(
                row,
                list(set(cols) - set(controlled_cols)),
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
            imported_sample_names.append(name)

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
        except SampleContentWarning as e:
            e.row = row_num
            warnings.warn(e)

    # remove samples in the existing_samples (input sample_set) but not in the input file
    extra_samples = set(existing_sample_names.keys()) - set(imported_sample_names)
    for extra_sample in extra_samples:
        del existing_sample_names[extra_sample]

    user_keys = set()
    for s in samples:
        for n in s['sample']['node_tree']:
            ukeys = set(n['meta_user'].keys())
            ckeys = set(n['meta_controlled'].keys())
            user_keys |= (ukeys - ckeys)
    for key in user_keys:
        warnings.warn(SampleContentWarning(
            f"User defined column {key} will be stored but not validated",
            key=key,
            severity='warning'
        ))

    # add the missing samples from existing_sample_names
    return samples, [existing_sample_names[key] for key in existing_sample_names]


def _save_samples(samples, acls, sample_url, token):
    """"""
    saved_samples = []
    for data in samples:
        sample = data['sample']
        prev_sample = data['prev_sample']
        name = data['name']

        sample_id, sample_ver = save_sample(sample, sample_url, token, previous_version=prev_sample)

        if sample_id:
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


def format_input_file(df, params, columns_to_input_names, aliases):
    # change columns to upload format
    columns_to_input_names = {}

    # set column names into 'upload_key_format'.
    for col_idx, col_name in enumerate(df.columns):
        renamed = upload_key_format(col_name)
        if renamed not in columns_to_input_names:
            columns_to_input_names[renamed] = col_name
        else:
            warnings.warn(SampleContentWarning(
                (f"Duplicate column \"{renamed}\". \"{col_name}\" would overwrite a different column \"{columns_to_input_names[renamed]}\". "
                "Rename your columns to be unique alphanumericaly, ignoring whitespace and case."),
                key=col_name,
                column = col_idx,
                severity='error'
            ))

    df = df.rename(columns={columns_to_input_names[col]: col for col in columns_to_input_names})
    df.replace({n: None for n in NOOP_VALS}, inplace=True)

    # TODO: Make sure to check all possible name fields, even when not parameterized
    if params.get('name_field'):
        name_field = upload_key_format(params.get('name_field'))
        if name_field not in list(df.columns):
            raise ValueError(
                f"The expected name field column \"{name_field}\" could not be found. "
                "Adjust your parameters or input such that the following are correct:\n"
                f"- File Format: {params.get('file_format')} (the format to which your sample data conforms)\n"
                f"- ID Field: {params.get('name_field','name')}\n (the header of the column containing your names)\n"
                f"- Headers Row: {params.get('header_row_index')} (the row # where column headers are located in your spreadsheet)"
            )
        # here we rename whatever the id field was/is to "id"
        columns_to_input_names["name"] = columns_to_input_names.pop(name_field)
        df.rename(columns={name_field: "name"}, inplace=True)

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

    file_format = params.get('file_format').lower()

    prefix_map = {}
    for col in df.columns:
        if ':' in col:
            continue
        fields = NON_PREFIX_TO_PREFIX.get(col, [])
        target_field = None
        for field in fields:
            # choose the format that fits if it exists.
            if field.split(":")[0] == file_format:
                target_field = field
                break
            else:
                if col in CORE_FIELDS:
                    target_field = col
                else:
                    target_field = field
        if target_field:
            prefix_map[col] = target_field
            if col in columns_to_input_names:
                val = columns_to_input_names.pop(col)
                columns_to_input_names[target_field] = val
    if prefix_map:
        df = df.rename(columns=prefix_map)

    return df, columns_to_input_names


def import_samples_from_file(
    params,
    sample_url,
    workspace_url,
    callback_url,
    username,
    token,
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
    ignore_warnings = params.get('ignore_warnings', 1) # TODO: default to 0 (false)
    with SampleContentWarningContext(ignore_warnings) as errors:
        # verify inputs
        sample_file = validate_params(params)
        ws_name = params.get('workspace_name')
        df = load_file(sample_file, header_row_index, date_columns)

        file_format = params['file_format'].lower()
        if 'sample_template' not in df:
            df['sample_template'] = file_format.upper()

        df, columns_to_input_names = format_input_file(df, params, {}, aliases)

        if not errors.get(severity='error'):
            if file_format in ['sesar', "enigma"]:
                if 'material' in df.columns:
                    df.rename(columns={"material": file_format + ":material"}, inplace=True)
                    val = columns_to_input_names.pop("material")
                    columns_to_input_names[file_format + ":material"] = val
            if file_format == "kbase":
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

            samples, existing_samples = _produce_samples(
                callback_url,
                df,
                column_groups,
                column_unit_regex,
                sample_url,
                token,
                input_sample_set['samples'],
                columns_to_input_names
            )

        # check when no new sample is created and samples in the input file matches exactly the given input sample_set
        if not samples and input_sample_set.get('samples') and len(input_sample_set.get('samples')) == len(existing_samples):
            error_msg = "No sample is produced from the input file.\n"
            error_msg += "The input sample set has identical information to the input file\n"

            raise ValueError(error_msg)

        if params.get('prevalidate') and not errors.get(severity='error') and samples:
            error_detail = validate_samples([s['sample'] for s in samples], sample_url, token)
            for e in error_detail:
                warnings.warn(SampleContentWarning(
                        e['message'],
                        sample_name=e['sample_name'],
                        node=e['node'],
                        key=e['key']
                    ))
    if errors.get():
        saved_samples = []

        # Calculate missing location information for SamplesContentError(s)
        err_col_keys = {}
        err_key_indices = {}
        for col_idx, col_name in enumerate(df.columns):
            err_col_keys[col_idx] = col_name
            err_key_indices[col_name] = col_idx
            if col_name in columns_to_input_names and columns_to_input_names[col_name] != col_name:
                err_key_indices[columns_to_input_names[col_name]] = col_idx

        err_row_sample_names = {}
        err_sample_name_indices = {}
        for row_num, row in df.iterrows():
            sample_name = row.get('name')
            err_sample_name_indices[sample_name] = row_num
            err_row_sample_names[row_num] = sample_name

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

    sample_data_json = df.to_json(orient='split')

    return {
        "samples": saved_samples,
        "description": params.get('description')
    }, errors.get(), sample_data_json
