import os
import time
import unittest
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from installed_clients.WorkspaceClient import Workspace
from installed_clients.SampleServiceClient import SampleService
from installed_clients.FakeObjectsForTestsClient import FakeObjectsForTests
from sample_uploader.utils.sample_utils import (
    get_data_links_from_ss,
    expire_data_link)


class SampleUtilsTest(unittest.TestCase):

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
        cls.test_dir = os.path.dirname(cls.curr_dir)
        cls.scratch = cls.cfg['scratch']
        cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/sampleservice'
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_sample_reads_linking_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.wsID = ret[0]
        cls.ss = SampleService(cls.sample_url, token=token)

        cls.sesar_sample_file = os.path.join(cls.test_dir, "data", "fake_samples.tsv")
        cls.sample_set_name = "test_sample_set_1"
        params = {
            'workspace_name': cls.wsName,
            'workspace_id': cls.wsID,
            'sample_file': cls.sesar_sample_file,
            'file_format': "sesar",
            'header_row_index': 2,
            'set_name': cls.sample_set_name,
            'description': "this is a test sample set.",
            'output_format': "",
            'name_field': "test name field",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
        }
        ret = cls.serviceImpl.import_samples(cls.ctx, params)[0]
        cls.sample_set = ret['sample_set']
        cls.sample_name_1 = cls.sample_set['samples'][0]['name']
        cls.sample_name_2 = cls.sample_set['samples'][1]['name']
        cls.sample_name_3 = cls.sample_set['samples'][2]['name']
        cls.sample_set_ref = ret['sample_set_ref']

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def createFakeReads(self):
        if hasattr(self.__class__, 'fake_reads_ref'):
            return self.__class__.fake_reads_ref

        obj_name = 'test_obj.1'
        foft = FakeObjectsForTests(self.callback_url, service_ver='dev')
        info = foft.create_fake_reads({'ws_name': self.wsName, 'obj_names': [obj_name]})[0]

        fake_reads_ref = "%s/%s/%s" % (info[6], info[0], info[4])

        self.__class__.fake_reads_ref = fake_reads_ref
        print('Loaded Fake Reads Object: ' + fake_reads_ref)
        return fake_reads_ref

    def test_expire_data_link(self):
        # create multiple data links for test object
        test_obj = self.createFakeReads()
        links_in = [
            {'sample_name': [self.sample_name_1], 'obj_ref': test_obj},
            {'sample_name': [self.sample_name_2], 'obj_ref': test_obj},
            {'sample_name': [self.sample_name_3], 'obj_ref': test_obj},
        ]

        ret = self.serviceImpl.link_samples(
            self.ctx, {
                'workspace_name': self.wsName,
                'sample_set_ref': self.sample_set_ref,
                'links': links_in,
            })

        links_out = [d['new_link'] for d in ret[0]['links']]

        assert len(links_out) == len(links_in)
        for lin, lout in zip(links_in, links_out):
            assert lout['linkid'] and lout['id'] and lout['version']
            assert lout['upa'] == lin['obj_ref']
            assert lout['node'] == lin['sample_name'][0]

        links_before = get_data_links_from_ss(test_obj, self.sample_url, self.ctx['token'])
        assert len(links_before) == len(links_in)

        expired_link_count = expire_data_link([test_obj], self.sample_url, self.ctx['token'])
        assert expired_link_count == len(links_in)

        links_after = get_data_links_from_ss(test_obj, self.sample_url, self.ctx['token'])
        assert len(links_after) == 0
