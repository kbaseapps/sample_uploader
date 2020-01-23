import requests
import uuid
import json
import os
import pandas as pd


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

    sample_columns = [s['name'] + " {"+ s['id'] +"}" for s in sample_set['samples']]
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


def update_acls(sample_url, sample_id, acls):
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


def generate_metadata(row, cols, groups):
    """"""
    # first we iterate through the groups
    metadata = {}
    used_cols = set([])
    for group in groups:
        mtd = {}
        if group['value'] not in cols:
            continue
        for val in group:
            # if starts with 'str:', not a column
            if group[val].startswith('str:'):
                mtd[val] = group[val][4:]
            # default behaviour expects a column as the value
            else:
                if not pd.isnull(row[group[val]]):
                    mtd[val] = row[group[val]]
                    used_cols.add(group[val])
        metadata[group["value"]] = mtd

    cols = list(set(cols) - used_cols)
    for col in cols:
        if not pd.isnull(row[col]):
            metadata[col] = {"value": row[col]}
    return metadata


def save_sample(sample, sample_url, token):
    """
    sample - completed sample as per 
    sample_url - url to sample service
    token - workspace token for Authorization
    """
    headers = {"Authorization": token}
    params = {
        "sample": sample,
        "prior_version": None,
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
    return sample_id
