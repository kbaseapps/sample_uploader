
# import os
# import unittest
# from configparser import ConfigParser
# from sample_uploader.authclient import KBaseAuth as _KBaseAuth

# from sample_uploader.utils.importer import import_samples_from_file
# from sample_uploader.utils.mappings import SESAR_mappings, ENIGMA_mappings


# class sample_uploaderTest(unittest.TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.token = os.environ.get('KB_AUTH_TOKEN', None)
#         config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
#         cls.cfg = {}
#         config = ConfigParser()
#         config.read(config_file)
#         for nameval in config.items('sample_uploader'):
#             cls.cfg[nameval[0]] = nameval[1]
#         authServiceUrl = cls.cfg['auth-service-url']
#         auth_client = _KBaseAuth(authServiceUrl)
#         cls.username = auth_client.get_user(cls.token)
#         cls.test_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
#         sample_server = cls.cfg.get('sample-server')
#         cls.sample_url = cls.cfg['kbase-endpoint'] + '/{}'.format(sample_server)
#         cls.workspace_url = cls.cfg['workspace-url']

#     @unittest.skip('works only with CI')
#     def test_ENIGMA_format(self):
#         # test default sample server
#         sample_file = os.path.join(self.test_dir, 'data', 'fake_samples_ENIGMA.xlsx')

#         params = {
#             'workspace_name': 'workspace_name',
#             'sample_file': sample_file,
#             'file_format': "ENIGMA",
#             'id_field': 'name',
#             'prevalidate': 1,
#         }
#         sample_server = self.cfg.get('sample-server')
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)
#         header_row_index = 1

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 ENIGMA_mappings['column_mapping'],
#                 ENIGMA_mappings.get('groups', []),
#                 ENIGMA_mappings['date_columns'],
#                 ENIGMA_mappings.get('column_unit_regex', []),
#                 {"samples": []},
#                 header_row_index
#             )

#         samples = sample_set['samples']
#         self.assertEqual(len(samples), 3)
#         expected_sample_name = ['Sample 1', 'Sample 2', 'Sample 3']
#         self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         self.assertEqual(len(errors), 0)

#         # test sampleservicetest sample server
#         sample_server = 'sampleservicetest'
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 ENIGMA_mappings['column_mapping'],
#                 ENIGMA_mappings.get('groups', []),
#                 ENIGMA_mappings['date_columns'],
#                 ENIGMA_mappings.get('column_unit_regex', []),
#                 {"samples": []},
#                 header_row_index
#             )

#         print('import samples output - ENIGMA')
#         print(sample_set)
#         print(errors)

#         # samples = sample_set['samples']
#         # self.assertEqual(len(samples), 3)
#         # expected_sample_name = ['Sample 1', 'Sample 2', 'Sample 3']
#         # self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         # self.assertEqual(len(errors), 0)

#     # @unittest.skip('works only with CI')
#     def test_import_SESAR_format(self):
#         # test default sample server
#         sample_file = os.path.join(self.test_dir, 'data', 'fake_samples.tsv')

#         params = {
#             'workspace_name': 'workspace_name',
#             'sample_file': sample_file,
#             'file_format': "SESAR",
#             'id_field': 'sample name',
#             'prevalidate': 1,
#         }
#         sample_server = self.cfg.get('sample-server')
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)
#         header_row_index = 1

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 SESAR_mappings['column_mapping'],
#                 SESAR_mappings.get('groups', []),
#                 SESAR_mappings['date_columns'],
#                 SESAR_mappings.get('column_unit_regex', []),
#                 {"samples": []},
#                 header_row_index
#             )

#         samples = sample_set['samples']
#         self.assertEqual(len(samples), 3)
#         expected_sample_name = ['Sample 1', 'Sample 2', 'Sample 3']
#         self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         self.assertEqual(len(errors), 0)

#         # test sampleservicetest sample server
#         sample_server = 'sampleservicetest'
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 SESAR_mappings['column_mapping'],
#                 SESAR_mappings.get('groups', []),
#                 SESAR_mappings['date_columns'],
#                 SESAR_mappings.get('column_unit_regex', []),
#                 {"samples": []},
#                 header_row_index
#             )

#         print('import samples output - SESAR')
#         print(sample_set)
#         print(errors)

#         # samples = sample_set['samples']
#         # self.assertEqual(len(samples), 3)
#         # expected_sample_name = ['Sample 1', 'Sample 2', 'Sample 3']
#         # self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         # self.assertEqual(len(errors), 0)

#     # @unittest.skip('works only with CI')
#     def test_KBASE_format(self):
#         # test default sample server
#         sample_file = os.path.join(self.test_dir, 'example_data', 'ncbi_sample_example.csv')
#         params = {
#             'workspace_name': 'workspace_name',
#             'sample_file': sample_file,
#             'file_format': "KBASE",
#             'id_field': 'id',
#             'prevalidate': 1,
#         }
#         sample_server = self.cfg.get('sample-server')
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)
#         header_row_index = 0

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 {},
#                 [],
#                 [],
#                 [],
#                 {"samples": []},
#                 header_row_index
#             )

#         samples = sample_set['samples']
#         self.assertEqual(len(samples), 2)
#         expected_sample_name = ['Seawater-16', 'SAMN04383980']
#         self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         self.assertEqual(len(errors), 0)

#         # test sampleservicetest sample server
#         sample_server = 'sampleservicetest'
#         sample_url = self.cfg['kbase-endpoint'] + '/{}'.format(sample_server)

#         sample_set, errors = import_samples_from_file(
#                 params,
#                 sample_url,
#                 self.workspace_url,
#                 self.username,
#                 self.token,
#                 {},
#                 [],
#                 [],
#                 [],
#                 {"samples": []},
#                 header_row_index
#             )

#         print('import samples output - KBASE')
#         print(sample_set)
#         print(errors)

#         # samples = sample_set['samples']
#         # self.assertEqual(len(samples), 2)
#         # expected_sample_name = ['Seawater-16', 'SAMN04383980']
#         # self.assertCountEqual([sample['name'] for sample in samples], expected_sample_name)
#         # self.assertEqual(len(errors), 0)
