# -*- coding: utf-8 -*-
import os
import time
import unittest
import requests
import uuid
import json
import pandas as pd
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from sample_uploader.utils.sample_utils import get_sample_service_url
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
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = sample_uploader(cls.cfg)
        cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.scratch = cls.cfg['scratch']
        cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = get_sample_service_url(cls.wiz_url)
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.wsID = ret[0]
        cls.test_files = [
            (
                os.path.join(cls.curr_dir, "data", "floc_mini_metadata.xls"),
                os.path.join(cls.curr_dir, "data", "floc_mini_metadata_cmp.json")
            ),(
                os.path.join(cls.curr_dir, "data", "flocs_all_metadata.xls"),
                os.path.join(cls.curr_dir, "data", "flocs_all_metadata_cmp.json")
            ),(
                os.path.join(cls.curr_dir, "data", "moss_f50_metadata.xls"),
                os.path.join(cls.curr_dir, "data", "moss_f50_metadata_cmp.json")
            )
        ]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')
    
    def compare_sample(self, s, sc):
        self.assertEqual(s['name'], sc['name'], msg=f"s: {json.dumps(s['name'])}\nsc: {json.dumps(sc['name'])}")
        self.assertEqual(s['node_tree'], sc['node_tree'], msg=f"s: {json.dumps(s['node_tree'])}\nsc: {json.dumps(sc['node_tree'])}")

    def verify_samples(self, sample_set, compare):
        for it, samp in enumerate(sample_set['samples']):
            samp_id = samp['id']
            headers = {"Authorization": self.ctx['token']}
            params = {
                "id": samp_id,
            }
            payload = {
                "method": "SampleService.get_sample",
                "id": str(uuid.uuid4()),
                "params": [params],
                "version": "1.1"
            }
            resp = requests.post(url=self.sample_url, headers=headers, data=json.dumps(payload))
            resp_json = resp.json()
            if resp_json.get('error'):
                raise RuntimeError(f"Error from SampleService - {resp_json['error']}")
            sample = resp_json['result'][0]
            self.compare_sample(sample, compare[it])

    def verify_output_file(self, sample_set, file_path, file_type, num_metadata_cols, num_otus):
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        elif file_type == 'xls':
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"file_type must be xls or csv not {file_type}")
        cols = list(df.columns)
        self.assertEqual(len(cols), len(sample_set['samples']) + 1 + num_metadata_cols, msg=f"number of columns in output file not correct: {cols}")

    # @unittest.skip('x')
    def test_upload_sample_from_csv(self):
        self.maxDiff = None
        # Prepare test objects in workspace if needed using
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2-forKB.csv")
        num_otus = 10
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'set_name': 'test1',
            'description': "this is a test sample set.",
            'output_format': 'csv',
            'num_otus': num_otus,
            'incl_seq': 1,
            'taxonomy_source': 'n/a',
            'otu_prefix': 'test_OTU'
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        with open(os.path.join(self.curr_dir, 'data', 'compare_to.json')) as f:
            compare_to = json.load(f)
        self.verify_samples(sample_set, compare_to)
        self.verify_output_file(
            sample_set, 
            os.path.join(self.scratch, os.path.basename(sample_file).split('.')[0] + '_OTU.csv'),
            'csv',
            3,
            num_otus
        )

    # @unittest.skip('x')
    def test_upload_sample_from_xls(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2.xls")
        num_otus = 10
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'set_name': 'test2',
            'description': "this is a test sample set.",
            'output_format': 'csv',
            'num_otus': num_otus,
            'incl_seq': 1,
            'taxonomy_source': 'n/a',
            'otu_prefix': 'test_OTU'
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        with open(os.path.join(self.curr_dir, 'data', 'compare_to.json')) as f:
            compare_to = json.load(f)
        self.verify_samples(sample_set, compare_to)
        self.verify_output_file(
            sample_set,
            os.path.join(self.scratch, os.path.basename(sample_file).split('.')[0] + '_OTU.csv'),
            'csv',
            3,
            num_otus
        )

    #@unittest.skip('x')
    def test_multiple_inputs(self):
        """"""
        self.maxDiff = None
        for sample_file, compare_file in self.test_files:
            ss_name = os.path.basename(sample_file).split('.')[0] + '_sample_set'
            params = {
                'workspace_name': self.wsName,
                'workspace_id': self.wsID,
                'sample_file': sample_file,
                'file_format': "SESAR",
                'set_name': ss_name,
                'description': "this is a test sample set.",
                'output_format': "",
            }
            ret = self.serviceImpl.import_samples(self.ctx, params)[0]
            with open(compare_file) as f:
                compare_to = json.load(f)
            self.verify_samples(ret['sample_set'], compare_to)

    # @unittest.skip('x')
    def test_generate_OTU_sheet(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2.xls")
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'set_name': 'test2',
            'description': "this is a test sample set.",
            'output_format': "",
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        sample_set = ret['sample_set']
        sample_set_ref = ret['sample_set_ref']
        num_otus = 20
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            "sample_set_ref": sample_set_ref,
            "output_name": "test_output",
            "output_format": "xls",
            "num_otus": num_otus,
            "taxonomy_source": "n/a",
            "incl_seq": 0,
            "otu_prefix": "science_is_cooool"
        }
        ret = self.serviceImpl.generate_OTU_sheet(self.ctx, params)[0]
        self.verify_output_file(
            sample_set,
            os.path.join(self.scratch, 'test_output.xlsx'),
            'xls',
            2,
            num_otus
        )
