import pandas as pd
import json
from sample_uploader.utils.sample_utils import get_sample
from sample_uploader.utils.mappings import SESAR_mappings  #, ENIGMA_mappings
from sample_uploader.utils.parsing_utils import (
    check_value_in_list,
    upload_key_format
)


def sample_set_to_output(sample_set, sample_url, token, output_file, output_file_format):
    """"""
    def add_to_output(o, key_metadata, val):
        if key_metadata in o:
            o[key_metadata] += [
                "" for _ in range(len(o['kbase_sample_id']) - 1 - len(o[key_metadata]))
            ] + [val]
        else:
            o[key_metadata] = [
                "" for _ in range(len(o['kbase_sample_id']) - 1)
            ] + [val]
        return o

    if output_file_format.lower() == "sesar":
        groups = SESAR_mappings['groups']
    else:
        raise ValueError(f"SESAR only file format supported for export")

    output = {"kbase_sample_id": [], "name": []}
    for samp_id in sample_set['samples']:
        sample = get_sample(samp_id, sample_url, token)
        output['kbase_sample_id'].append(sample['id'])
        # we need to check if there is another match in there.
        sample_name = sample['name']

        output['name'].append(sample_name)
        used_headers = set(['kbase_sample_id', 'name'])
        for node_idx, node in enumerate(sample['node_tree']):
            # check if node 'id' and sample 'name' are not the same
            if node['id'] != sample_name:
                output = add_to_output(output, f"alt_id_{node_idx}",node['id'])
            # get 'source_meta' information
            source_meta = node.get('source_meta', [])
            source_meta_key = {m['key']: m['skey'] for m in source_meta}
            for key_metadata in node['meta_controlled']:
                # get original input key
                upload_key = source_meta_key.get(key_metadata, key_metadata)
                if upload_key not in used_headers:
                    for key, val in node['meta_controlled'][key_metadata].items():
                        if key == 'value':
                            output = add_to_output(output, upload_key, val)
                            used_headers.add(upload_key)
                        if key == 'units':
                            idx = check_value_in_list(key_metadata, [upload_key_format(g['value']) for g in groups], return_idx=True)
                            if idx is not None and not groups[idx]['units'].startswith('str:'):
                                output = add_to_output(output, groups[idx]['units'], val)
                                used_headers.add(groups[idx]['units'])

            for key_metadata in node['meta_user']:
                # get original input key
                upload_key = source_meta_key.get(key_metadata, key_metadata)
                if upload_key not in used_headers:
                    for key, val in node['meta_user'][key_metadata].items():
                        if key == 'value':
                            output = add_to_output(output, upload_key, val)
                            used_headers.add(upload_key)
                        if key == 'units':
                            idx = check_value_in_list(key_metadata, [upload_key_format(g['value']) for g in groups], return_idx=True)
                            if idx is not None and not groups[idx]['units'].startswith('str:'):
                                output = add_to_output(output, groups[idx]['units'], val)

    # add any missing lines to the end.
    for key in output:
        output[key] += ["" for _ in range(len(output['kbase_sample_id']) - len(output[key]))]

    df = pd.DataFrame.from_dict(output)

    def line_prepender(filename, line):
        with open(filename, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(line.rstrip('\r\n') + '\n' + content)

    df.to_csv(output_file, index=False)

    if output_file_format.lower() == "sesar":
        line_prepender(output_file, "Object Type:,Individual Sample,User Code:,")
