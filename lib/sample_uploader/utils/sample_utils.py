import requests
import uuid
import json
import os
import re
import pandas as pd

from sample_uploader.utils.mappings import SAMP_SERV_CONFIG
from sample_uploader.utils.parsing_utils import (
    parse_grouped_data,
    check_value_in_list,
    handle_groups_metadata
)
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.WorkspaceClient import Workspace as workspaceService
from installed_clients.SampleServiceClient import SampleService


def _handle_response(resp):
    """
    resp - response object from request to SampleService
    """
    if not resp.ok:
        try:
            resp_data = json.loads(resp.text)
            resp_mess = resp_data['error']['message']
        except:
            resp_mess = str(resp.text)
        raise RuntimeError(f"{resp_mess}")
    resp_json = resp.json()
    if resp_json.get('error'):
        try:
            resp_mess = resp_json['error']['message']
        except:
            resp_mess = resp_json['error']
        raise RuntimeError(f"{resp_mess}")
    return resp_json


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


def update_acls(sample_url, sample_id, acl_updates, token):
    """
    Query sample service to replace access control list for given sample id.
        sample_url - url of sample service
        sample_id - id of sample as given by sample service
        change_acls - dictionary string keys and list values mapping access type to username.
            {
                "admin": ["user1", "user3", ...],
                "write": ["user2", ..],
                "read": ["user4"],
                "remove": ["user5", ...]
            }
        "owner" value currently not updateable
    """
    headers = {"Authorization": token}

    UpdateSampleACLsParams = {
        "id": sample_id,
        "admin": acl_updates.get("admin", []),
        "write": acl_updates.get("write", []),
        "read": acl_updates.get("read", []),
        "remove": acl_updates.get("remove", []),
        "at_least": False
    }
    replace_payload = {
        "method": "SampleService.update_sample_acls",
        "id": str(uuid.uuid4()),
        "params": [UpdateSampleACLsParams],
        "version": "1.1"
    }

    resp = requests.post(url=sample_url, data=json.dumps(replace_payload), headers=headers)
    _ = _handle_response(resp)
    return resp.status_code


def generate_source_meta(row, contr_meta_keys, columns_to_input_names):
    """
    """
    source_meta = []
    # for col, val in row.iteritems():
    for col in contr_meta_keys:
        val = row.get(col)
        source_meta.append({
            'key': col,
            'skey': columns_to_input_names.get(col),
            'svalue': {
                "value": val
            }
        })
    return source_meta


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
            except (ValueError, TypeError):
                val = row[col]
            metadata[col] = {"value": val}
            if units:
                metadata[col]["units"] = units

    return metadata


def generate_controlled_metadata(row, groups):
    """
    row - row from input pandas.DataFrame object to convert to metadata
    groups - list of dicts - each dict is a grouping where key = "metadata field name" (i.e. "value
    ", or "units") and value = input file column name
    """
    metadata = {}
    used_cols = set([])
    # use the shared fields
    for col, val in row.iteritems():
        ss_validator = SAMP_SERV_CONFIG['validators'].get(col, None)
        # check if `col` is controlled metadata
        if ss_validator:
            # check if value associated with `col`, we don't store empty values
            if not pd.isnull(row[col]):
                idx = check_value_in_list(col, [g['value'] for g in groups], return_idx=True)
                try:
                    val = float(row[col])
                except (ValueError, TypeError):
                    val = row[col]
                mtd = {"value": val}
                # checking if there is a "grouping" for the metadata field `col`
                # "grouping" = two or more columns compose into one metadata field
                idx = check_value_in_list(col, [g['value'] for g in groups], return_idx=True)
                if idx is not None:
                    mtd, grouped_used_cols = parse_grouped_data(row, groups[idx])
                    used_cols.update(grouped_used_cols)

                # verify against validator
                missing_fields = _find_missing_fields(mtd, ss_validator)
                for field, default in missing_fields.items():
                    mtd[field] = default

                col_type = ss_validator.get('key_metadata', {}).get('type')
                if col_type == 'string':
                    mtd['value'] = str(mtd['value'])

                metadata[col] = mtd
                used_cols.add(col)

    return metadata, used_cols


def _find_missing_fields(mtd, ss_validator):
    missing_fields = {}
    for val in ss_validator.get('validators'):
        if val.get('parameters'):
            for key in ['key', 'keys']:
                if val['parameters'].get(key):
                    if val['parameters'][key] not in mtd:
                        missing_fields[val['parameters'][key]] = val['parameters'][val['parameters'][key]]
    return missing_fields


def compare_samples(s1, s2):
    """
    return True if samples are the same,
        does not compare source_meta field
    s1, s2 - samples with the following fields:
        'node_tree', 'name'
    """

    if s1 is None or s2 is None:
        return False
    else:

        def remove_field(node, field):
            if field in node:
                node.pop(field)
            return node
        # don't compare 'source_meta' field
        s1_nt = [remove_field(n, 'source_meta') for n in s1['node_tree']]
        s2_nt = [remove_field(n, 'source_meta') for n in s2['node_tree']]

        # TODO: worth scrutiny
        comp = s1['name'] == s2['name'] and s1_nt == s2_nt
        return comp


def get_sample(sample_info, sample_url, token):
    """ Get sample from SampleService
    sample_info - dict containing 'id' and 'version' of a sample
    sample_url - SampleService Url
    token      - Authorization token
    """
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
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
    # print('-'*80)
    # print('get sample')
    # print('url', sample_url)
    # print('payload', json.dumps(payload))    
    # print('-'*80)
    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload))
    resp_json = _handle_response(resp)
    sample = resp_json['result'][0]
    return sample


def save_sample(sample, sample_url, token, previous_version=None, propagate_links=0):
    """
    sample     - completed sample as per
    sample_url - url to sample service
    token      - workspace token for Authorization
    previous_version - data of previous version of sample
    """
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    if previous_version:
        prev_sample = get_sample({"id": previous_version["id"]}, sample_url, token)
        if compare_samples(sample, prev_sample):
            return None, None
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
    # print('-'*80)
    # print('save sample')
    # print('url', sample_url)
    # print('payload', json.dumps(payload))    
    # print('-'*80)
    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload, default=str))
    resp_json = _handle_response(resp)
    sample_id = resp_json['result'][0]['id']
    sample_ver = resp_json['result'][0]['version']

    if previous_version and propagate_links:

        ss = SampleService(sample_url)
        ss.propagate_data_links({'id': sample_id,
                                 'version': sample_ver,
                                 'previous_version': previous_version['version'],
                                 'ignore_types': ['KBaseSets.SampleSet'],
                                 'update': True,
                                 'as_user': True})

    return sample_id, sample_ver


def validate_samples(samples, sample_url, token):
    """
    samples    - list of Sample
    sample_url - url to sample service
    token      - workspace token for Authorization
    """
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    params = {
        "samples": samples
    }
    payload = {
        "method": "SampleService.validate_samples",
        "id": str(uuid.uuid4()),
        "params": [params],
        "version": "1.1"
    }
    # print('-'*80)
    # print('validate samples')
    # print('url', sample_url)
    # print('payload', json.dumps(payload))    
    # print('-'*80)
    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload, default=str))
    resp_json = _handle_response(resp)
    errors = resp_json['result'][0]['errors']
    return errors


def get_data_links_from_ss(sample_set_ref, sample_url, token):
    """
    fetch data links associated with sample set object
    sample_set_ref - ref of a sample set object
    sample_url     - url to sample service
    token          - workspace token for Authorization
    """
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    params = {
        "upa": sample_set_ref
    }
    payload = {
        "method": "SampleService.get_data_links_from_data",
        "id": str(uuid.uuid4()),
        "params": [params],
        "version": "1.1"
    }

    resp = requests.post(url=sample_url, headers=headers, data=json.dumps(payload, default=str))
    resp_json = _handle_response(resp)

    links = resp_json['result'][0].get('links')

    return links


def get_data_links_from_sample(sample_id, version, sample_url, token):
    """
    sample_id      - the sample ID.
    version        - the sample version.
    sample_url     - url to sample service
    token          - workspace token for Authorization
    """
    ss = SampleService(sample_url, token=token)
    ret = ss.get_data_links_from_sample({'id': sample_id, 'version': version})

    return ret.get('links')


def format_sample_as_row(sample, sample_headers=None, file_format="SESAR"):
    """"""
    if sample_headers:
        sample_headers = sample_headers.split(',')

    def metadata_to_str(meta_controlled, meta_user, used_headers):
        r_str = []
        if sample_headers:
            for key_metadata in sample_headers:
                used_headers.add(key_metadata)
                if key_metadata in meta_controlled:
                    for key, val in meta_controlled[key_metadata].items():
                        if key == "value":
                            r_str.append(str(val))
                elif key_metadata in meta_user:
                    for key, val in meta_user[key_metadata].items():
                        if key == "value":
                            r_str.append(str(val))
                else:
                    r_str.append("")
        else:
            raise RuntimeError(f"No sample headers provided -- {sample_headers}")
        return ",".join(r_str), used_headers

    if file_format == "SESAR":
        header_str = "kbase_sample_id,Sample name"
        row_str = str(sample['id']) + ',' + str(sample['name'])
        used_headers = set(["kbase_sample_id", "name"])
        i = 0
        for node in sample['node_tree']:
            r_str, used_headers = metadata_to_str(node['meta_controlled'], node['meta_user'], used_headers)
            row_str += "," + r_str
            i = 1 + i
        return header_str.strip() + '\n', row_str.strip() + '\n'
    else:
        return None, None


def build_links(input_staging_file_path, callback_url, workspace_url, workspace_id, token):

    if not input_staging_file_path:
        raise ValueError('Missing batch links file')

    dfu = DataFileUtil(url=callback_url)
    wsClient = workspaceService(workspace_url, token=token)
    download_staging_file_params = {
        'staging_file_subdir_path': input_staging_file_path
    }
    scratch_file_path = dfu.download_staging_file(
        download_staging_file_params).get('copy_file_path')

    df = pd.read_csv(scratch_file_path, sep=None)

    required_headers = ['sample_name', 'object_name']
    check = all(header in df.columns for header in required_headers)
    if not check:
        raise ValueError('Missing {} in header'.format(required_headers))

    links = list()
    for idx, row in df.iterrows():
        sample_name = row['sample_name']
        object_name = row['object_name']

        # get numerical object reference (valid UPA for samples link)
        obj_ref_chain = '{}/{}'.format(workspace_id, object_name)
        obj_info = wsClient.get_object_info3({
            'objects': [{"ref": obj_ref_chain}], 'includeMetadata': 0})["infos"][0]
        obj_ref = "%s/%s/%s" % (obj_info[6], obj_info[0], obj_info[4])

        links.append({'sample_name': [sample_name], 'obj_ref': obj_ref})

    return links


def expire_data_link(obj_refs, sample_url, token):
    ss = SampleService(sample_url, token=token)
    expired_link_count = 0
    for upa in obj_refs:
        links = get_data_links_from_ss(upa, sample_url, token)
        for link in links:
            upa, dataid = link.get('upa'), link.get('dataid')
            ss.expire_data_link({'upa': upa, 'dataid': dataid})
            expired_link_count += 1

    return expired_link_count
