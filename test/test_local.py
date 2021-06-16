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
from sample_uploader.utils.sample_utils import get_sample
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
        cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL, token=token)
        cls.serviceImpl = sample_uploader(cls.cfg)
        # cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.scratch = cls.cfg['scratch']
        # cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/sampleservice'
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.wsID = ret[0]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')


    def compare_sample(self, s, sc, check_version=True, check_id=False):
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

    def verify_samples(self, sample_set, compare_path):
        with open(compare_path) as f:
            compare = json.load(f)
        # print('[')
        for it, samp in enumerate(sample_set['samples']):
            sample = get_sample(samp, self.sample_url, self.ctx['token'])
            # print(json.dumps(sample), ',')
            self.compare_sample(sample, compare[it])
        # print(']')

    def get_local_data_file(self, filename):
        data = [
            ["SampleID", "sample name", "material"],
            ["s1", "sample 1", "ENVO:00002041"],
            ["s2", "sample 2", "ENVO:00002007"]
        ]
        with open(filename, 'w') as f:
            for line in data:
                f.write('\t'.join(line) + "\n")
        return data

    # @unittest.skip('Only for local tests. Not part of official test suite.')
    def test_local(self):
        self.maxDiff = None
        local_file = "local_data.tsv"
        os.mkdir(os.path.join(self.scratch, "data"))
        sample_file = os.path.join(self.scratch, "data", local_file)
        data = self.get_local_data_file(sample_file)
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "enigma",
            'header_row_index': 1,  # 1-indexed
            'set_name': 'test1',
            'description': "this is a test SampleSet.",
            'output_format': '',
            'incl_input_in_output': 1,
            'prevalidate': 1
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        print(sample_set)
        # self.verify_samples(
        #     sample_set,
        #     os.path.join(self.curr_dir, 'data', 'compare_to_update.json')
        # )
