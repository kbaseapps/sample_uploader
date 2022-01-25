import os
import time
import unittest
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
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
        cls.token = token
        cls.username = user_id
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

        sample_set_1_file = os.path.join(cls.curr_dir, 'example_data', 'isgn_sample_example.csv')
        params = {
            'workspace_name': cls.wsName,
            'workspace_id': cls.wsID,
            'sample_file': sample_set_1_file,
            'file_format': "sesar",
            'header_row_index': 2,
            'set_name': 'sample_set_1',
            'description': "this is a test sample set.",
            'output_format': "",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
            'ignore_warnings': 1
        }
        ret = cls.serviceImpl.import_samples(cls.ctx, params)[0]
        cls.sample_set_1 = ret['sample_set']
        cls.sample_set_1_id = ret['sample_set']['samples'][0]['id']
        cls.sample_set_1_ref = ret['sample_set_ref']

        sample_set_2_file = os.path.join(
            cls.curr_dir, 'example_data', 'ANLPW_JulySamples_IGSN_v2-forKB.csv')
        params = {
            'workspace_name': cls.wsName,
            'workspace_id': cls.wsID,
            'sample_file': sample_set_2_file,
            'file_format': "sesar",
            'header_row_index': 2,
            'set_name': 'sample_set_2',
            'description': "this is a test sample set.",
            'output_format': "",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
            'ignore_warnings': 1
        }
        ret = cls.serviceImpl.import_samples(cls.ctx, params)[0]
        cls.sample_set_2 = ret['sample_set']
        cls.sample_set_2_id = ret['sample_set']['samples'][0]['id']
        cls.sample_set_2_ref = ret['sample_set_ref']

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def filter(self, sets, conditions):
        ''''''
        ret = self.serviceImpl.filter_samplesets(self.ctx, {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'out_sample_set_name': "filtered_" + str(int(time.time() * 1000)),
            'sample_set_ref': sets,
            'filter_conditions': conditions
        })

        return ret[0]['sample_set']['samples']

    def test_filter_number_gt(self):
        ''''''
        samples_gt = self.filter([self.sample_set_1_ref], [{
            'metadata_field': "latitude",
            'comparison_operator': ">=",
            'value': "25",
            'logical_operator': "AND",
        }])

        self.assertEqual(len(samples_gt), 2)
        self.assertEqual(set(sample['name'] for sample in samples_gt),
                         set(['PB-Low-5', 'Core 1-1*-1M']))

    def test_filter_number_lt(self):
        samples_lt = self.filter([self.sample_set_1_ref], [{
            'metadata_field': "latitude",
            'comparison_operator': "<=",
            'value': "25",
            'logical_operator': "AND",
        }])

        self.assertEqual(len(samples_lt), 1)
        self.assertEqual(set(sample['name'] for sample in samples_lt),
                         set(['ww163e']))

    def test_filter_number_eq(self):
        samples_eq = self.filter([self.sample_set_1_ref], [{
            'metadata_field': "longitude",
            'comparison_operator': "==",
            'value': "-92.1833",
            'logical_operator': "AND",
        }])

        self.assertEqual(len(samples_eq), 1)
        self.assertEqual(set(sample['name'] for sample in samples_eq),
                         set(['Core 1-1*-1M']))

    def test_merge_sets_string_eq(self):
        samples_merge = self.filter([self.sample_set_1_ref, self.sample_set_2_ref], [{
            'metadata_field': "sesar:collection_method",
            'comparison_operator': "==",
            'value': "Coring > Syringe",
            'logical_operator': "AND",
        }])
        self.assertEqual(len(samples_merge), 207)

    def test_str_in(self):
        samples_merge = self.filter([self.sample_set_2_ref], [{
            'metadata_field': "sesar:collection_method",
            'comparison_operator': "in",
            'value': "Coring > Syringe, Grab",
            'logical_operator': "AND",
        }])
        self.assertEqual(len(samples_merge), 209)

    def test_and(self):
        samples_merge = self.filter([self.sample_set_2_ref], [
            {
                'metadata_field': "sesar:collection_method",
                'comparison_operator': "==",
                'value': "Coring > Syringe",
                'logical_operator': "AND",
            },
            {
                'metadata_field': "latitude",
                'comparison_operator': ">",
                'value': "33.33",
                'logical_operator': "OR",
            }
        ])
        self.assertEqual(len(samples_merge), 160)

    def test_or(self):
        samples_merge = self.filter([self.sample_set_2_ref], [
            {
                'metadata_field': "sesar:collection_method",
                'comparison_operator': "==",
                'value': "Coring > Syringe",
                'logical_operator': "OR",
            },
            {
                'metadata_field': "latitude",
                'comparison_operator': ">",
                'value': "33.33",
                'logical_operator': "AND",
            }
        ])
        self.assertEqual(len(samples_merge), 210)

    def test_order_of_ops(self):
        samples_merge = self.filter([self.sample_set_2_ref], [
            {
                'metadata_field': "sesar:collection_method",
                'comparison_operator': "==",
                'value': "Coring > Syringe",
                'logical_operator': "OR",
            },
            {
                'metadata_field': "latitude",
                'comparison_operator': ">",
                'value': "33.33",
                'logical_operator': "AND",
            },
            {
                'metadata_field': "longitude",
                'comparison_operator': "<",
                'value': "81.718",
                'logical_operator': "OR",
            }
        ])
        self.assertEqual(len(samples_merge), 206)

    @unittest.skip("deprecated method, called from UI directly")
    def test_get_sampleset_meta(self):
        ret = self.serviceImpl.get_sampleset_meta(self.ctx, {
            'sample_set_refs': [self.sample_set_2_ref]
        })
        self.assertEqual(type(ret[0]), list)
        self.assertEqual(type(ret[0][0]), str)
        self.assertCountEqual(ret[0], [
            'sesar:igsn',
            'sesar:material',
            'location_description',
            'locality_description',
            'sesar:collection_method',
            'purpose',
            'latitude',
            'longitude',
            'sesar:navigation_type',
            'sesar:physiographic_feature_primary',
            'sesar:physiographic_feature_name',
            'sesar:field_program_cruise',
            'sesar:collector_chief_scientist',
            'sesar:collection_date',
            'sesar:collection_date_precision',
            'sesar:archive_current',
            'sesar:archive_contact_current',
            'sesar:related_identifiers',
            'sesar:relation_type',
            'sample_template',
            'custom:coordinate_precision?',
            'sesar:release_date',
            'sesar:elevation_start',
            'sesar:field_name'
        ])
