# -*- coding: utf-8 -*-
import os
import time
import unittest
import requests
import uuid
import json
import shutil
import pandas as pd
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from sample_uploader.utils.sample_utils import get_sample_service_url, get_sample
from installed_clients.WorkspaceClient import Workspace

class sample_uploaderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('sample_uploader'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'sample_uploader',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL, token=token)
        cls.serviceImpl = sample_uploader(cls.cfg)
        cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.scratch = cls.cfg['scratch']
        cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = get_sample_service_url(cls.wiz_url)
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_sample_uploader_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.wsID = ret[0]
        cls.sesar_sample_file = os.path.join(cls.curr_dir, "data", "fake_samples.tsv")
        cls.sample_set_name = "test_sample_set_1"
        params = {
            'workspace_name': cls.wsName,
            'workspace_id': cls.wsID,
            'sample_file':  cls.sesar_sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': cls.sample_set_name,
            'description': "this is a test sample set.",
            'output_format': "",
            'id_field': "test id field",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
        }
        ret = cls.serviceImpl.import_samples(cls.ctx, params)[0]
        cls.sample_set = ret['sample_set']
        cls.a_sample_id = ret['sample_set']['samples'][0]['id']
        cls.sample_set_ref = ret['sample_set_ref']
        # add new user to test permissions
        cls.wsClient.set_permissions({
            "id": cls.wsID,
            "new_permission": "w",
            "users": ["psdehal"]
        })

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # @unittest.skip('x')
    def test_SESAR_file(self):
        ''''''
        compare_path = os.path.join(self.curr_dir, "data", "fake_samples.json")
        self._verify_samples(self.sample_set, compare_path)

    # @unittest.skip('x')
    def test_ENIGMA_file(self):
        ''''''
        sample_file = os.path.join(self.curr_dir, 'data', 'fake_samples_ENIGMA.xlsx')
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 2,
            'set_name': "test_sample_set_2",
            'description': "this is a test sample set.",
            'output_format': "csv",
            'prevalidate': 1,
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        sample_set = ret['sample_set']
        sample_set_ref = ret ['sample_set_ref']
        compare_path = os.path.join(self.curr_dir, 'data', 'fake_samples_ENIGMA.json')
        self._verify_samples(sample_set, compare_path)
        # next we test if the update functionality is working
        # make copy of file in scratch
        os.mkdir(os.path.join(self.scratch, 'temporary_data'))
        enigma_copy = os.path.join(self.scratch, 'temporary_data', os.path.basename(sample_file))
        # now alter the file in a couple places
        alter = {
            0: ("Jamboree", 'user data'),
            2: ("latitude", 30)
        }
        df = pd.read_excel(sample_file, header=1)
        for idx in alter:
            df.at[idx, alter[idx][0]] = alter[idx][1]
        # now write dataframe to new file location
        df.to_excel(enigma_copy, index=False)
        params = {
            'sample_set_ref': sample_set_ref,
            'sample_file': enigma_copy,
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'file_format': "ENIGMA",
            'header_row_index': 1,
            'description': "this is a copy of a test sample set.",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
        }
        sample_set_2 = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        ss2 = {s['name']: s for s in sample_set_2['samples']}
        # check that s1 and s3 were updated and s2 was not.
        for it, samp1 in enumerate(sample_set['samples']):
            # get sample by name
            name = samp1['name']
            sample1 = get_sample(samp1, self.sample_url, self.ctx['token'])
            sample2 = get_sample(ss2.get(samp1['name']), self.sample_url, self.ctx['token'])
            if name == 'Sample 2':
                self._compare_sample(sample1, sample2)
            else:
                try:
                    assert sample2['version'] > sample1['version']
                    assert sample2['id'] == sample1['id']
                    node2 = sample2['node_tree'][0]
                    node1 = sample1['node_tree'][0]
                    if name == 'Sample 1':
                        assert node2['meta_user']['jamboree']['value'] == 'user data'
                    elif name == 'Sample 3':
                        assert node2['meta_controlled']['latitude']['value'] == 30
                except:
                    raise ValueError(f"could not compare samples:\n{json.dumps(sample1)}\n{json.dumps(sample2)}")

    def test_IGSN_sample_importer(self):
        igsns = ['IEAWH0001', 'GEE0000O4', 'ODP000002']

        # test list igsns input
        params = {
            'igsns': igsns,
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'description': "test sample set from IGSNs",
            'set_name': 'test_sample_set_igsn'
        }
        ret = self.serviceImpl.import_samples_from_IGSN(self.ctx, params)[0]
        samples_info = ret['sample_set']['samples']

        assert len(samples_info) == len(igsns)

        samples = [get_sample(sample_info, self.sample_url, self.ctx['token'])
                   for sample_info in samples_info]

        sample_ids = [sample['node_tree'][0]['id'] for sample in samples]
        assert set(sample_ids) == set(igsns)

        expected_sample_names = ['PB-Low-5', 'ww163e', 'Core 1-1*-1M']
        sample_names = [sample['name'] for sample in samples]
        assert set(expected_sample_names) == set(sample_names)

        # test string igsns input with multiple IGSNs
        params = {
            'igsns': ', '.join(igsns),
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'description': "test sample set from IGSNs",
            'set_name': 'test_sample_set_igsn'
        }
        ret = self.serviceImpl.import_samples_from_IGSN(self.ctx, params)[0]
        samples_info = ret['sample_set']['samples']

        assert len(samples_info) == len(igsns)

        samples = [get_sample(sample_info, self.sample_url, self.ctx['token'])
                   for sample_info in samples_info]

        sample_ids = [sample['node_tree'][0]['id'] for sample in samples]
        assert set(sample_ids) == set(igsns)

        expected_sample_names = ['PB-Low-5', 'ww163e', 'Core 1-1*-1M']
        sample_names = [sample['name'] for sample in samples]
        assert set(expected_sample_names) == set(sample_names)

        # test string igsns input with single IGSN
        igsns = igsns[0]
        params = {
            'igsns': igsns,
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'description': "test sample set from IGSNs",
            'set_name': 'test_sample_set_igsn'
        }
        ret = self.serviceImpl.import_samples_from_IGSN(self.ctx, params)[0]
        samples_info = ret['sample_set']['samples']

        assert len(samples_info) == 1

        sample = get_sample(samples_info[0], self.sample_url, self.ctx['token'])

        sample_id = sample['node_tree'][0]['id']
        assert sample_id == igsns

        expected_sample_names = 'PB-Low-5'
        sample_name = sample['name']
        assert expected_sample_names == sample_name

    # @unittest.skip('x')
    def test_error_file(self):
        ''''''
        sample_file = os.path.join(self.curr_dir, 'data', 'error_file.csv')
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 2,
            'set_name': "test_sample_set_2",
            'description': "this is a test sample set.",
            'prevalidate': 1,
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        # check errors
        self.assertTrue(ret.get('errors'))
        with open(os.path.join(self.curr_dir, 'data', 'error_match.json')) as f:
            expected_errors = json.load(f)
        for sample_name, errors in ret['errors'].items():
            self.assertEqual(expected_errors.get(sample_name), errors)

    # @unittest.skip('x')
    def test_export(self):
        '''Make sure the samples are the same after download, then reupload'''
        params = {
            "input_ref": self.sample_set_ref,
            "file_format": "SESAR"
        }
        ret = self.serviceImpl.export_samples(self.ctx, params)[0]
        shock_id = ret['shock_id']
        result_dir = ret['result_dir']
        result_file_name = '_'.join(self.sample_set_name.split()) + ".csv"
        self.assertTrue(result_file_name in os.listdir(result_dir))
        result_file_path = os.path.join(result_dir, result_file_name)
        # now run with output as input to import samples.
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': result_file_path,
            'file_format': "SESAR",
            'header_row_index': 2,
            'id_field': 'test id field',
            'set_name': 'reupload_test',
            'description': "this is a test sample set.",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        self._compare_sample_sets(self.sample_set, ret['sample_set'])

    # @unittest.skip('x')
    def test_change_acls(self):
        ''''''
        self.maxDiff = None
        params = {
            'workspace_id': self.wsID,
            'new_users': [
                "eapearson"
            ],
            'is_admin': 1,
            'is_reader': 0,
            'is_writer': 0,
            'sample_set_ref': self.sample_set_ref,
        }
        ret = self.serviceImpl.update_sample_set_acls(self.ctx, params)[0]
        self.assertEqual(ret['status'], 200)
        payload = {
            "method": "SampleService.get_sample_acls",
            "id": str(uuid.uuid4()),
            "params": [{"id": self.a_sample_id}],
            "version": "1.1"
        }
        resp = requests.get(
            url=self.sample_url,
            data=json.dumps(payload),
            headers={"Authorization": self.ctx['token']}
        )
        resp_json = resp.json()
        resp_data = {}
        for category in resp_json['result'][0]:
            if category == "owner":
                resp_data[resp_json['result'][0]['owner']] = 'a'
            elif category == "public_read":
                continue
            else:
                for name in resp_json['result'][0][category]:
                    resp_data[name] = category[0]
        self.assertTrue('eapearson' in resp_data and resp_data['eapearson'] == 'a')

    def _compare_sample(self, s, sc, check_version=True, check_id=False):
        self.assertEqual(s['name'], sc['name'], msg=f"s: {json.dumps(s['name'])}\nsc: {json.dumps(sc['name'])}")
        # self.assertEqual(s['node_tree'], sc['node_tree'], msg=f"s: {json.dumps(s['node_tree'])}\nsc: {json.dumps(sc['node_tree'])}")
        for i, s_node in enumerate(s['node_tree']):
            sc_node = sc['node_tree'][i]
            # check all fields except 'source_meta'
            if 'source_meta' in s_node:
                s_node.pop('source_meta')
            if 'source_meta' in sc_node:
                sc_node.pop('source_meta')
            self.assertEqual(s_node, sc_node, msg=f"s: {json.dumps(s_node)}\nsc: {json.dumps(sc_node)}")
        if check_version:
            self.assertEqual(s['version'], sc['version'], msg=f"s: {json.dumps(s['version'])}\nsc: {json.dumps(sc['version'])}")
        if check_id:
            self.assertEqual(s['id'], sc['id'])

    def _compare_sample_sets(self, sample_set, sample_set_2):
        sample_set_2 = {sam['name']: sam for sam in sample_set_2['samples']}
        for it, samp in enumerate(sample_set['samples']):
            self.assertTrue(sample_set_2.get(samp['name']))
            sample = get_sample(samp, self.sample_url, self.ctx['token'])
            sample2 = get_sample(sample_set_2[samp['name']], self.sample_url, self.ctx['token'])
            # print('gen sample', sample)
            # print('jsn sample', sample2)
            self._compare_sample(sample, sample2, check_id=True, check_version=True)

    def _verify_samples(self, sample_set, compare_path):
        with open(compare_path) as f:
            compare = json.load(f)
        # print('[')
        for it, samp in enumerate(sample_set['samples']):
            sample = get_sample(samp, self.sample_url, self.ctx['token'])
            # print(json.dumps(sample), ',')
            self._compare_sample(sample, compare[it])
        # print(']')

    def _verify_output_file(self, sample_set, file_path, file_type, num_metadata_cols, num_otus):
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        elif file_type == 'xls':
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"file_type must be xls or csv not {file_type}")
        cols = list(df.columns)
        self.assertEqual(len(cols), len(sample_set['samples']) + 1 + num_metadata_cols, msg=f"number of columns in output file not correct: {cols}")
