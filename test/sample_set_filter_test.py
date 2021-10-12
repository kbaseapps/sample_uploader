import os
import time
import unittest
import uuid
import json
import shutil
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from sample_uploader.utils.sample_utils import get_sample
from installed_clients.WorkspaceClient import Workspace
from installed_clients.SampleServiceClient import SampleService

class Test(unittest.TestCase):

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
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/sampleservice'
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_sample_reads_linking_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.wsID = ret[0]
        cls.ss = SampleService(cls.sample_url, token=token)
        if 'appdev' in cls.cfg['kbase-endpoint']:
            cls.ReadLinkingTestSampleSet = '44442/4/1'
            cls.rhodo_art_jgi_reads = '44442/8/1'
            cls.rhodobacter_art_q20_int_PE_reads = '44442/6/1'
            cls.rhodobacter_art_q50_SE_reads = '44442/7/2'
        elif 'ci' in cls.cfg['kbase-endpoint']:
            cls.ReadLinkingTestSampleSet = '59862/11/1' # SampleSet
            cls.rhodo_art_jgi_reads = '59862/8/4' # paired
            cls.rhodobacter_art_q20_int_PE_reads = '59862/6/1' # paired
            cls.rhodobacter_art_q50_SE_reads = '59862/5/1' # single

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def test_sample_set_filter(self):

        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'out_sample_set_name': "foo_out",
            'sample_set_ref': ['one','two','three'],
            'filter_conditions': [{
                'column':"foo_col",
                'comparison':"==",
                'value':"99",
                'condition':"AND",
            }]
        };

        ret = self.serviceImpl.filter_samplesets(
            self.ctx, params)

        print(ret)


# Appdev
# ReadLinkingTestSampleSet = '44442/4/1'
# rhodo_art_jgi_reads = '44442/8/1'
# rhodobacter_art_q20_int_PE_reads = '44442/6/1'
# rhodobacter_art_q50_SE_reads = '44442/7/2'

# CI (not publicly available TODO)
# SampleMetaData_tsv_sample_set = '59862/2/1' # SampleSet
# ReadLinkingTestSampleSet = '59862/11/1' # SampleSet
# Example_Reads_Libraries = '59862/9/1' # ReadsSet
# rhodo_art_jgi_reads = '59862/8/4' # paired
# rhodobacter_art_q10_PE_reads = '59862/7/1' # paired
# rhodobacter_art_q20_int_PE_reads = '59862/6/1' # paired
# rhodobacter_art_q50_SE_reads = '59862/5/1' # single
