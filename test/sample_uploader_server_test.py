# -*- coding: utf-8 -*-
import os
import time
import unittest
import requests
import uuid
import json
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

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')
    
    def compare_sample(self, s, sc):
        self.assertEqual(s['name'], sc['name'])
        self.assertEqual(s['node_tree'], sc['node_tree'])

    def verify_samples(self, sample_set, compare):
        token = self.ctx['token']
        for it, samp_id in enumerate(sample_set['sample_ids']):
            headers = {"Authorization": token}
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

    # @unittest.skip('x')
    def test_upload_sample_from_csv(self):
        # Prepare test objects in workspace if needed using
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2-forKB.csv")
        params = {
            'workspace_name': self.wsName,
            'sample_file': sample_file,
            'file_format': "SESAR"
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]
        with open(os.path.join(self.curr_dir, 'data', 'compare_to.json')) as f:
            compare_to = json.load(f)
        self.verify_samples(sample_set, compare_to)

    # @unittest.skip('x')
    def test_upload_sample_from_xls(self):
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2.xls")
        params = {
            'workspace_name': self.wsName,
            'sample_file': sample_file,
            'file_format': "SESAR"
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]
        with open(os.path.join(self.curr_dir, 'data', 'compare_to.json')) as f:
            compare_to = json.load(f)
        self.verify_samples(sample_set, compare_to)
