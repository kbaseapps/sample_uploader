
import os
import unittest
import json
from configparser import ConfigParser
from sample_uploader.authclient import KBaseAuth as _KBaseAuth

from sample_uploader.utils.importer import import_samples_from_file
from sample_uploader.utils.mappings import SESAR_mappings, ENIGMA_mappings, aliases
from sample_uploader.utils.sample_utils import get_sample


class sample_uploaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('sample_uploader'):
            cls.cfg[nameval[0]] = nameval[1]
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        cls.username = auth_client.get_user(cls.token)
        cls.test_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        sample_server = cls.cfg.get('sample-server', 'sampleservice')
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/{}'.format(sample_server)
        cls.workspace_url = cls.cfg['workspace-url']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

    def _verify_samples(self, sample_set, compare_path):
        with open(compare_path) as f:
            compare = json.load(f)

        for it, samp in enumerate(sample_set['samples']):
            sample = get_sample(samp, self.sample_url, self.token)
            self._compare_sample(sample, compare[it])

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

    # @unittest.skip('x')
    def test_ENIGMA_format(self):
        # test default sample server
        sample_file = os.path.join(self.test_dir, 'data', 'fake_samples_ENIGMA.xlsx')

        params = {
            'workspace_name': 'workspace_name',
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'name_field': 'name',
            'prevalidate': 1,
        }

        header_row_index = 1

        mappings = {'enigma': ENIGMA_mappings, 'sesar': SESAR_mappings, 'kbase': {}}
        sample_set, errors, sample_data_json = import_samples_from_file(
            params,
            self.sample_url,
            self.workspace_url,
            self.callback_url,
            self.username,
            self.token,
            mappings[str(params.get('file_format')).lower()].get('groups', []),
            mappings[str(params.get('file_format')).lower()].get('date_columns', []),
            mappings[str(params.get('file_format')).lower()].get('column_unit_regex', []),
            {"samples": []},
            header_row_index,
            aliases
        )

        print('import samples output - ENIGMA')
        print(sample_set)
        print(errors)

        samples = sample_set['samples']
        self.assertEqual(len(samples), 3)
        expected_sample_name = ['s1', 's2', 's3']
        self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
        self.assertEqual(len(errors), 0)

        compare_path = os.path.join(self.test_dir, "data", "fake_samples_ENIGMA_1.json")
        self._verify_samples(sample_set, compare_path)

    # @unittest.skip('x')
    def test_import_SESAR_format(self):
        # test default sample server
        sample_file = os.path.join(self.test_dir, 'data', 'fake_samples.tsv')

        params = {
            'workspace_name': 'workspace_name',
            'sample_file': sample_file,
            'file_format': "SESAR",
            'name_field': 'test name field',
            'prevalidate': 1,
        }
        header_row_index = 1

        mappings = {'enigma': ENIGMA_mappings, 'sesar': SESAR_mappings, 'kbase': {}}
        sample_set, errors, sample_data_json = import_samples_from_file(
            params,
            self.sample_url,
            self.workspace_url,
            self.callback_url,
            self.username,
            self.token,
            mappings[str(params.get('file_format')).lower()].get('groups', []),
            mappings[str(params.get('file_format')).lower()].get('date_columns', []),
            mappings[str(params.get('file_format')).lower()].get('column_unit_regex', []),
            {"samples": []},
            header_row_index,
            aliases
        )

        print('import samples output - SESAR')
        print(sample_set)
        print(errors)

        samples = sample_set['samples']
        self.assertEqual(len(samples), 3)
        expected_sample_name = ['s1', 's2', 's3']
        self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
        self.assertEqual(len(errors), 0)

        compare_path = os.path.join(self.test_dir, "data", "fake_samples_1.json")
        self._verify_samples(sample_set, compare_path)

    # @unittest.skip('x')
    def test_KBASE_format(self):
        # test default sample server
        sample_file = os.path.join(self.test_dir, 'example_data', 'ncbi_sample_example.csv')
        params = {
            'workspace_name': 'workspace_name',
            'sample_file': sample_file,
            'file_format': "KBASE",
            'id_field': 'id',
            'prevalidate': 1,
        }
        header_row_index = 0

        mappings = {'enigma': ENIGMA_mappings, 'sesar': SESAR_mappings, 'kbase': {}}
        sample_set, errors, sample_data_json = import_samples_from_file(
            params,
            self.sample_url,
            self.workspace_url,
            self.callback_url,
            self.username,
            self.token,
            mappings[str(params.get('file_format')).lower()].get('groups', []),
            mappings[str(params.get('file_format')).lower()].get('date_columns', []),
            mappings[str(params.get('file_format')).lower()].get('column_unit_regex', []),
            {"samples": []},
            header_row_index,
            aliases
        )

        print('import samples output - KBASE')
        print(sample_set)
        print(errors)

        samples = sample_set['samples']
        self.assertEqual(len(samples), 2)
        expected_sample_name = ['SAMN03166112', 'SAMN04383980']
        self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
        self.assertEqual(len(errors), 0)
