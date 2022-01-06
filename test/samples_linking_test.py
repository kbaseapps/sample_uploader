import os
import time
import unittest
from configparser import ConfigParser
from unittest.mock import patch
import pandas as pd
import uuid

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from installed_clients.WorkspaceClient import Workspace
from installed_clients.SampleServiceClient import SampleService
from installed_clients.DataFileUtilClient import DataFileUtil
from sample_uploader.utils.sample_utils import get_sample, get_data_links_from_sample


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

        cls.sesar_sample_file = os.path.join(cls.curr_dir, "data", "fake_samples.tsv")
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

        if 'appdev' in cls.cfg['kbase-endpoint']:
            cls.ReadLinkingTestSampleSet = '44442/4/1'
            cls.rhodo_art_jgi_reads = '44442/8/1'
            cls.rhodobacter_art_q20_int_PE_reads = '44442/6/1'
            cls.rhodobacter_art_q50_SE_reads = '44442/7/2'
            cls.test_genome = '44442/16/1'
            cls.test_genome_name = 'test_genome'
            cls.test_assembly_SE_reads = '44442/15/1'
            cls.test_assembly_SE_reads_name = 'single_end_kbassy'
            cls.test_assembly_PE_reads = '44442/14/1'
            cls.test_assembly_PE_reads_name = 'kbassy_roo_f'
            cls.test_AMA_genome = '44442/13/2'
            cls.target_wsID = 44442
        elif 'ci' in cls.cfg['kbase-endpoint']:
            cls.ReadLinkingTestSampleSet = '59862/11/1'  # SampleSet
            cls.rhodo_art_jgi_reads = '59862/8/4'  # paired
            cls.rhodobacter_art_q20_int_PE_reads = '59862/6/1'  # paired
            cls.rhodobacter_art_q50_SE_reads = '59862/5/1'  # single
            cls.test_genome = '59862/27/1'
            cls.test_genome_name = 'test_Genome'
            cls.test_assembly_SE_reads = '59862/26/1'
            cls.test_assembly_SE_reads_name = 'single_end_kbassy'
            cls.test_assembly_PE_reads = '59862/25/1'
            cls.test_assembly_PE_reads_name = 'kbassy_roo_f'
            cls.test_AMA_genome = '59862/28/1'
            cls.target_wsID = 59862

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def mock_download_staging_file(params):
        print('Mocking DataFileUtilClient.download_staging_file')
        print(params)

        file_path = params.get('staging_file_subdir_path')

        return {'copy_file_path': file_path}

    def test_overwrite_samples(self):

        # create initial test sample set
        sesar_sample_file = os.path.join(self.curr_dir, "data", "fake_samples.tsv")
        sample_set_name = "test_sample_set_1"
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sesar_sample_file,
            'file_format': "sesar",
            'header_row_index': 2,
            'set_name': self.sample_set_name,
            'description': "this is a test sample set.",
            'output_format': "",
            'name_field': "test name field"
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        sample_set = ret['sample_set']
        sample_set_ref = ret['sample_set_ref']

        # create data link for each sample
        links_in = [
            {'sample_name': [self.sample_name_1], 'obj_ref': self.rhodo_art_jgi_reads},
            {'sample_name': [self.sample_name_2],
             'obj_ref': self.rhodobacter_art_q20_int_PE_reads},
            {'sample_name': [self.sample_name_3],
             'obj_ref': self.rhodobacter_art_q50_SE_reads},
        ]

        ret = self.serviceImpl.link_samples(
            self.ctx, {
                'workspace_name': self.wsName,
                'sample_set_ref': sample_set_ref,
                'links': links_in,
            })

        links_out = [d['new_link'] for d in ret[0]['links']]

        assert len(links_out) == len(links_in)
        for lin, lout in zip(links_in, links_out):
            assert lout['linkid'] and lout['id'] and lout['version']
            assert lout['upa'] == lin['obj_ref']
            assert lout['node'] == lin['sample_name'][0]

        for it, samp in enumerate(sample_set['samples']):
            sample_id = samp['id']
            version = samp['version']
            data_links = get_data_links_from_sample(sample_id, version,
                                                    self.sample_url, self.ctx['token'])
            links_upa = [link['upa'] for link in data_links]
            expected_links = [links_in[it]['obj_ref'], sample_set_ref]
            self.assertCountEqual(links_upa, expected_links)

        # overwrite existing sample set

        # updated the 'Country' metadata
        new_sample_file = os.path.join(self.curr_dir, "data", "fake_samples_2.tsv")

        # test oerwritting without 'propagate_links' (default action)
        sample_set_name = "test_sample_set_2"
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_set_ref': sample_set_ref,
            'sample_file': new_sample_file,
            'file_format': "sesar",
            'header_row_index': 2,
            'set_name': sample_set_name,
            'description': "this is a test sample set.",
            'output_format': "",
            'name_field': "test name field",
        }

        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        new_sample_set = ret['sample_set']
        new_sample_set_ref = ret['sample_set_ref']

        for it, samp in enumerate(new_sample_set['samples']):
            sample = get_sample(samp, self.sample_url, self.ctx['token'])
            assert sample['node_tree'][0]['meta_controlled']['country']['value'] == 'USA'

            sample_id = samp['id']
            version = samp['version']
            self.assertEqual(version, 2)
            data_links = get_data_links_from_sample(sample_id, version,
                                                    self.sample_url, self.ctx['token'])

            links_upa = [link['upa'] for link in data_links]
            expected_links = [new_sample_set_ref]
            self.assertCountEqual(links_upa, expected_links)

    def test_link_samples(self):
        links_in = [
            {'sample_name': [self.sample_name_1], 'obj_ref': self.rhodo_art_jgi_reads},
            {'sample_name': [self.sample_name_2],
             'obj_ref': self.rhodobacter_art_q20_int_PE_reads},
            {'sample_name': [self.sample_name_3],
             'obj_ref': self.rhodobacter_art_q50_SE_reads},
            {'sample_name': [self.sample_name_3], 'obj_ref': self.test_genome},
            {'sample_name': [self.sample_name_3], 'obj_ref': self.test_assembly_SE_reads},
            {'sample_name': [self.sample_name_3], 'obj_ref': self.test_assembly_PE_reads},
            {'sample_name': [self.sample_name_3], 'obj_ref': self.test_AMA_genome},
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

        # test unsupported object type
        links_in = [
            {'sample_name': [self.sample_name_1], 'obj_ref': self.sample_set_ref},
        ]

        expected_error = 'Unsupported object type [KBaseSets.SampleSet]. Please provide one of'
        with self.assertRaises(ValueError) as context:
            self.serviceImpl.link_samples(
                self.ctx, {
                    'workspace_name': self.wsName,
                    'sample_set_ref': self.sample_set_ref,
                    'links': links_in,
                })

        self.assertIn(expected_error, str(context.exception.args[0]))

        # test missing sample_set_ref
        expected_error = 'Missing sample set object'
        with self.assertRaises(ValueError) as context:
            self.serviceImpl.link_samples(
                self.ctx, {
                    'workspace_name': self.wsName,
                    'links': links_in,
                })

        self.assertIn(expected_error, str(context.exception.args[0]))

    @patch.object(DataFileUtil, "download_staging_file", side_effect=mock_download_staging_file)
    def test_batch_link_samples(self, download_staging_file):

        # build test file
        input_staging_file_path = os.path.join(
            'data',
            'batch_link_sample_test_{}.tsv'.format(str(uuid.uuid4())))
        sample_names = [self.sample_name_1, self.sample_name_2, self.sample_name_3]
        obj_names = [self.test_genome_name, self.test_assembly_SE_reads_name,
                     self.test_assembly_PE_reads_name]

        data = {'sample_name': sample_names, 'object_name': obj_names}
        df = pd.DataFrame(data)
        df.to_csv(input_staging_file_path)

        ret = self.serviceImpl.batch_link_samples(
            self.ctx, {
                'workspace_name': self.wsName,
                'workspace_id': self.target_wsID,
                'sample_set_ref': self.sample_set_ref,
                'input_staging_file_path': input_staging_file_path,
            })

        links_out = [d['new_link'] for d in ret[0]['links']]
        assert len(links_out) == df.shape[0]
        for sample_name, obj_name, lout in zip(sample_names, obj_names, links_out):
            assert lout['linkid'] and lout['id'] and lout['version']
            assert lout['node'] == sample_name

        # test missing sample_name or object_name header
        input_staging_file_path = os.path.join('data', 'fake_samples.tsv')
        expected_error = "Missing ['sample_name', 'object_name'] in header"
        with self.assertRaises(ValueError) as context:
            self.serviceImpl.batch_link_samples(
                self.ctx, {
                    'workspace_name': self.wsName,
                    'sample_set_ref': self.sample_set_ref,
                    'input_staging_file_path': input_staging_file_path,
                })

        self.assertIn(expected_error, str(context.exception.args[0]))

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
