import requests
import uuid
import json
import pandas as pd


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
    resp_json = resp.json()
    if resp_json.get('error'):
        raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
    sample_id = resp_json['result'][0]['id']
    return sample_id
