import requests
import uuid
import json
import os
import re
import pandas as pd

from sample_uploader.utils.mappings import shared_fields, SAMP_SERV_CONFIG
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
    metadata, used_cols = handle_groups_metadata(row, cols, groups)
    cols = list(set(cols) - used_cols)
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
            # try to assing value as a float if possible
            try:
                val = float(row[col])
            except:
                val = row[col]
            metadata[upload_key_format(col)] = {"value": val}
            if units:
                metadata[upload_key_format(col)]["units"] = units

    return metadata


def generate_controlled_metadata(row, groups):
    """
    row  - row from input pandas.DataFrame object to convert to metadata
    cols - columns of input pandas.DataFrame to conver to metadata
    """
    metadata = {}
    # use the shared fields
    for col in shared_fields:
        col = upload_key_format(col)
        ss_validator = SAMP_SERV_CONFIG['validators'].get(col, None)
        if ss_validator:
            if col in row and not pd.isnull(row[col]):
                idx = check_value_in_list(col, [upload_key_format(g['value']) for g in groups], return_idx=True)
                try:
                    val = float(row[col])
                except:
                    val = row[col]
                mtd = {"value": val}
                if idx is not None:
                    mtd, _ = parse_grouped_data(row, groups[idx])
                # verify against validator
                missing_fields = _find_missing_fields(mtd, ss_validator)
                for field, default in missing_fields.items():
                    mtd[field] = default
                metadata[col] = mtd

    return metadata


def _find_missing_fields(mtd, ss_validator):
    missing_fields = {}
    for val in ss_validator.get('validators'):
        if val.get('parameters'):
            for key in ['key', 'keys']:
                if val['parameters'].get(key):
                    if val['parameters'][key] not in mtd:
                        missing_fields[val['parameters'][key]] = val['parameters'][val['parameters'][key]]
    return missing_fields


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
    sample     - completed sample as per 
    sample_url - url to sample service
    token      - workspace token for Authorization
    previous_version - previous version of sample
    """
    headers = {"Authorization": token}
    if previous_version:
        sample['id'] = previous_version['id']
        params = {
            "sample": sample,
            "prior_version": previous_version['version'],
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
        print('-'*80)
        print('-'*80)
        print("broken sample:", sample)
        print('-'*80)
        print('-'*80)
        raise RuntimeError(f'Error from SampleService - {resp.text}')
    resp_json = resp.json()
    if resp_json.get('error'):
        raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
    sample_id = resp_json['result'][0]['id']
    sample_ver = resp_json['result'][0]['version']
    return sample_id, sample_ver
