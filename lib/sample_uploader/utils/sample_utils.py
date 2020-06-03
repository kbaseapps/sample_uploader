import requests
import uuid
import json
import os
import re
import pandas as pd

from sample_uploader.utils.mappings import shared_fields
from sample_uploader.utils.parsing_utils import (
    parse_grouped_data,
    check_value_in_list,
    handle_groups_metadata,
    upload_key_format
)


def sample_set_to_OTU_sheet(
        sample_set,
        output_file_name,
        scratch,
        params
    ):
    """
    """
    number_of_OTUs = params.get('num_otus', 10)
    output_format = params.get('output_format', 'csv')
    otu_prefix = params.get('otu_prefix', 'OTU')

    metadata_cols = []
    if params.get('taxonomy_source', None):
        metadata_cols += ['taxonomy', 'taxonomy_source']
    if params.get('incl_seq', False):
        metadata_cols += ['consensus_sequence']

    sample_columns = [str(s['name']) + " {"+ str(s['id']) +"} (" + str(s['version']) + ")" for s in sample_set['samples']]
    OTU_ids = [otu_prefix + '_' + str(i+1) for i in range(number_of_OTUs)] 
    data = {'OTU id': OTU_ids}
    data.update(
        {c: [None for _ in range(number_of_OTUs)] for c in metadata_cols + sample_columns}
    )
    df = pd.DataFrame(
        data=data
    )
    if output_format == 'csv':
        if '.csv' not in output_file_name:
            output_file_name += '.csv'
        output_path = os.path.join(scratch, output_file_name)
        df.to_csv(output_path, index=False)
    elif output_format == 'xls':
        if '.xlsx' not in output_file_name:
            output_file_name += '.xlsx'
        # right now we only write to one sheet for excel
        output_path = os.path.join(scratch, output_file_name)
        df.to_excel(output_path, index=False)

    return output_path


def update_acls(sample_url, sample_id, acls, token):
    """
    Query sample service to replace access control list for given sample id.
        sample_url - url of sample service
        sample_id - id of sample as given by sample service
        acls - dictionary string keys and list values mapping access type to username.
            {
                "admin": ["user1", "user3", ...],
                "write": ["user2", ..],
                "read": ["user4"]
            }
        "owner" value currently not updateable
    """
    headers = {"Authorization": token}
    ReplaceSampleACLsParams = {
        "acls": acls,
        "id": sample_id
    }
    payload = {
        "method": "SampleService.replace_sample_acls",
        "id": str(uuid.uuid4()),
        "params": [ReplaceSampleACLsParams],
        "version": "1.1"
    }
    resp = requests.post(url=sample_url, data=json.dumps(payload), headers=headers)
    resp_json = resp.json()
    if resp_json.get('error'):
        raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
    return resp.status_code


def get_sample_service_url(sw_url):
    """"""
    payload = {
        "method":"ServiceWizard.get_service_status",
        "id":'',
        "params":[{"module_name":"SampleService","version":"dev"}], # TODO: change to beta/release
        "version":"1.1"
    }

    sw_resp  = requests.post(url=sw_url, data=json.dumps(payload))
    wiz_resp = sw_resp.json()
    if wiz_resp.get('error'):
        raise RuntimeError("ServiceWizard Error - "+ str(wiz_resp['error']))
    return wiz_resp['result'][0]['url']


def generate_user_metadata(row, cols, groups, unit_rules):
    """
    row        - row from input pandas.DataFrame object to convert to metadata
    cols       - columns of input pandas.DataFrame to conver to metadata
    groups     - list of dictionaries to group in same metadata field
    unit_rules - list of regexes that capture the units associated with all fields.
                 the first entry is used before the second which is used before the third and so on..
                 NOTE: empty list is valid input and results in no unit fields captured from regex.
    """
    # first we iterate through the groups
    # metadata = {}
    # used_cols = set([])
    # for group in groups:
    #     mtd = {}
    #     if group['value'] not in cols:
    #         continue
    #     for val in group:
    #         # if starts with 'str:', not a column
    #         if group[val].startswith('str:'):
    #             mtd[val] = group[val][4:]
    #         # default behaviour expects a column as the value
    #         else:
    #             if not pd.isnull(row[group[val]]):
    #                 mtd[val] = row[group[val]]
    #                 used_cols.add(group[val])
    #     metadata[group["value"]] = mtd
    metadata, used_cols = handle_groups_metadata(row, cols, groups)

    cols = list(set(cols) - used_cols)
    # print('+'*80)
    # print('current row:', row)
    # print('groups:', groups)
    # print('metadata from groups:',metadata)
    # print('used_columns from groups:', used_cols)
    # print('left over cols', cols)
    # print('+'*80)

    for col in cols:
        # col = col.lower( )
        if not pd.isnull(row[col]):
            # if there are column unit rules
            units = None
            if unit_rules:
                for unit_rule in unit_rules:
                    result = re.search(unit_rule, col)
                    if result:
                        # we assume the regex has capturing parantheses.
                        match = result.group(1)
                        units = match
                        # use only first match.
                        break
            if units:
                metadata[upload_key_format(col)] = {"value": row[col], "units": units}
            else:
                metadata[upload_key_format(col)] = {"value": row[col]}
    return metadata


def generate_controlled_metadata(row, groups):
    """
    row  - row from input pandas.DataFrame object to convert to metadata
    cols - columns of input pandas.DataFrame to convert to metadata
    """
    metadata = {}
    # use the shared fields from the mapping.
    # row_cols = row.columns
    # row.rename(columns = {r: r.lower() for r in row_cols}, inplace=True)

    for col in shared_fields:
        # make sure the column is lowercase
        # col = col.lower()
        # check if column exists in row.
        if col in row and not pd.isnull(row[col]):
            col = col.strip()
            idx = check_value_in_list(col, [g['value'] for g in groups], return_idx=True)
            if idx:
                # metadata[col_map[col]] = {"value": row[col]}
                mtd, _ = parse_grouped_data(row, groups[idx])
                metadata[upload_key_format(col)] = mtd
            else:
                metadata[upload_key_format(col)] = {"value": row[col]}
    return metadata


def get_sample(sample_info, sample_url, token):
    """ Get sample from SampleService
    sample_info - dict containing 'id' and 'version' of a sample
    sample_url - SampleService Url
    token      - Authorization token
    """
    headers = {"Authorization": token}
    params = {
        "id": sample_info['id']
    }
    if sample_info.get('version'):
        params['version'] = sample_info['version']
    payload = {
        "method": "SampleService.get_sample",
        "id": str(uuid.uuid4()),
        "params": [params],
        "version": "1.1"
    }
    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload))
    resp_json = resp.json()
    if resp_json.get('error'):
        raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
    sample = resp_json['result'][0]
    return sample


def save_sample(sample, sample_url, token, previous_version=None):
    """
    sample           - Sample
    sample_url       - url to sample service
    token            - workspace token for Authorization
    previous_version - previous version of sample
    """
    headers = {"Authorization": token}
    if previous_version:
        sample['id'] = previous_version['id']
        params = {
            "sample": sample,
            "prior_version": previous_version['version']
        }
    else:
        params = {
            "sample": sample,
            "prior_version": None
        }
    payload = {
        "method": "SampleService.create_sample",
        "id": str(uuid.uuid4()),
        "params": [params],
        "version": "1.1"
    }
    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload, default=str))
    if not resp.ok:
        raise RuntimeError(f'Error from SampleService - {resp.text}')
    resp_json = resp.json()
    if resp_json.get('error'):
        raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
    sample_id = resp_json['result'][0]['id']
    sample_ver = resp_json['result'][0]['version']
    return sample_id, sample_ver


def format_sample_as_row(sample, sample_headers=None, file_format="SESAR"):
    """"""
    if sample_headers:
        sample_headers = sample_headers.split(',')

    def metadata_to_str(metadata, used_headers):
        h_str, r_str = [], []
        if sample_headers:
            for key_metadata in sample_headers:
                if key_metadata not in used_headers:
                    h_str.append(str(key_metadata))
                    used_headers.add(str(key_metadata))
                    if key_metadata in metadata:
                        for key, val in metadata[key_metadata].items():
                            if key == "value":
                                r_str.append(str(val))
                    else:
                        r_str.append("")
        else:
            for key_metadata, values in metadata.items():
                if key_metadata not in used_headers:
                    h_str.append(str(key_metadata))
                    used_headers.add(str(key_metadata))
                    for key, val in values.items():
                        if key == "value":
                            r_str.append(str(val))

        return ",".join(h_str), ",".join(r_str), used_headers

    if file_format == "SESAR":
        header_str = "kbase_sample_id,Sample name"
        row_str = str(sample['id']) + ',' + str(sample['name'])
        used_headers = set(["kbase_sample_id", "name"])
        i = 0
        for node in sample['node_tree']:
            h_str, r_str, used_headers = metadata_to_str(node['meta_controlled'], used_headers)
            if i == 0 and not sample_headers:
                print('-')
                print('controlled rows:', r_str, '--', used_headers)
            if h_str and r_str:
                header_str += "," + h_str
                row_str += "," + r_str
            h_str, r_str, used_headers = metadata_to_str(node['meta_user'], used_headers)
            if i == 0 and not sample_headers:
                print('user row:', r_str, '--', used_headers)
            if h_str and r_str:
                header_str += "," + h_str
                row_str += "," +r_str
            i = 1 + i
        return header_str + '\n', row_str + '\n'
    else:
        return None, None
