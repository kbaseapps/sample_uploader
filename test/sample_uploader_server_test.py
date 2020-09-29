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
        sample_file = os.path.join(cls.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2.xls")
        cls.sample_set_name = "test2"
        params = {
            'workspace_name': cls.wsName,
            'workspace_id': cls.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': cls.sample_set_name,
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = cls.serviceImpl.import_samples(cls.ctx, params)[0]
        cls.sample_set = ret['sample_set']
        cls.sample_set_ref = ret['sample_set_ref']
        cls.update_test_files = False

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

    def compare_sample_sets(self, sample_set, sample_set_2):
        sample_set_2 = {sam['name']: sam for sam in sample_set_2['samples']}
        for it, samp in enumerate(sample_set['samples']):
            self.assertTrue(sample_set_2.get(samp['name']))
            sample = get_sample(samp, self.sample_url, self.ctx['token'])
            sample2 = get_sample(sample_set_2[samp['name']], self.sample_url, self.ctx['token'])
            # print('gen sample', sample)
            # print('jsn sample', sample2)

            self.compare_sample(sample, sample2, check_id=True, check_version=True)

    def verify_samples(self, sample_set, compare_path):
        if self.update_test_files:
            samples = []
            for it, samp in enumerate(sample_set['samples']):
                sample = get_sample(samp, self.sample_url, self.ctx['token'])
                samples.append(sample)
            with open(compare_path, 'w') as f:
                json.dump(samples, f)
        else:
            with open(compare_path) as f:
                compare = json.load(f)
            # print('[')
            for it, samp in enumerate(sample_set['samples']):
                sample = get_sample(samp, self.sample_url, self.ctx['token'])
                # print(json.dumps(sample), ',')
                self.compare_sample(sample, compare[it])
            # print(']')

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
    def test_user_defined_column(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "floc_mini_metadata_copy.xls")
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': "user_defined_columns",
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        self.verify_samples(
            sample_set,
            os.path.join(self.curr_dir, 'data', 'floc_mini_metadata_copy_cmp.json')
        )


    @unittest.skip('Only for local tests. Not part of official test suite.')
    def test_local(self):
        self.maxDiff = None
        local_file = "Marcins_data.tsv"
        sample_file = os.path.join(self.curr_dir, "data", local_file)
        num_otus = 10
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 1,
            'set_name': 'test1',
            'description': "this is a test sample set.",
            'output_format': '',
            "incl_input_in_output": 1
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        self.verify_samples(
            sample_set,
            os.path.join(self.curr_dir, 'data', 'compare_to_update.json')
        )

    # @unittest.skip('x')
    def test_export_samples(self):
        self.maxDiff = None
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
        df = pd.read_csv(result_file_path, header=1)
        # now run with output as input to import samples.
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': result_file_path,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': 'reupload_test',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        self.compare_sample_sets(self.sample_set, ret['sample_set'])

    # @unittest.skip('x')
    def test_update_samples(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2_copy.xls")
        params = {
            'sample_set_ref': self.sample_set_ref,
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': 'update_test',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        sample_set = ret['sample_set']
        self.verify_samples(
            sample_set,
            os.path.join(self.curr_dir, 'data', 'compare_to_update.json')
        )

    @unittest.skip('Currently broken, because of date columns.')
    def test_upload_SESAR_sample_from_csv(self):
        self.maxDiff = None
        # Prepare test objects in workspace if needed using
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2-forKB.csv")
        num_otus = 10
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': 'test1',
            'description': "this is a test sample set.",
            'output_format': 'csv',
            'num_otus': num_otus,
            'incl_seq': 1,
            'taxonomy_source': 'n/a',
            'otu_prefix': 'test_OTU'
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        self.verify_samples(
            sample_set,
            os.path.join(self.curr_dir, 'data', 'compare_to.json')
        )
        self.verify_output_file(
            sample_set, 
            os.path.join(self.scratch, os.path.basename(sample_file).split('.')[0] + '_OTU.csv'),
            'csv',
            3,
            num_otus
        )

    # @unittest.skip('x')
    def test_upload_SESAR_sample_from_xls(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "ANLPW_JulySamples_IGSN_v2.xls")
        num_otus = 10
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "SESAR",
            'header_row_index': 2,
            'set_name': 'test2',
            'description': "this is a test sample set.",
            'output_format': 'csv',
            'num_otus': num_otus,
            'incl_seq': 1,
            'taxonomy_source': 'n/a',
            'otu_prefix': 'test_OTU',
            "incl_input_in_output": 1
        }
        sample_set = self.serviceImpl.import_samples(self.ctx, params)[0]['sample_set']
        self.verify_samples(
            sample_set,
            os.path.join(self.curr_dir, 'data', 'compare_to.json')
        )
        self.verify_output_file(
            sample_set,
            os.path.join(self.scratch, os.path.basename(sample_file).split('.')[0] + '_OTU.csv'),
            'csv',
            3,
            num_otus
        )

    # @unittest.skip('x')
    def test_SESAR_multiple_inputs(self):
        """"""
        self.maxDiff = None
        for sample_file, compare_file in self.test_files:
            ss_name = os.path.basename(sample_file).split('.')[0] + '_sample_set'
            params = {
                'workspace_name': self.wsName,
                'workspace_id': self.wsID,
                'sample_file': sample_file,
                'file_format': "SESAR",
                'header_row_index': 2,
                'set_name': ss_name,
                'description': "this is a test sample set.",
                'output_format': "",
                "incl_input_in_output": 1
            }
            ret = self.serviceImpl.import_samples(self.ctx, params)[0]
            self.verify_samples(
                ret['sample_set'],
                compare_file
            )

    # @unittest.skip('x')
    def test_SESAR_generate_OTU_sheet(self):
        self.maxDiff = None
        num_otus = 20
        sample_set = self.sample_set
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            "sample_set_ref": self.sample_set_ref,
            "output_name": "test_output",
            "output_format": "xls",
            "num_otus": num_otus,
            "taxonomy_source": "n/a",
            "incl_seq": 0,
            "otu_prefix": "science_is_cooool",
        }
        ret = self.serviceImpl.generate_OTU_sheet(self.ctx, params)[0]
        self.verify_output_file(
            sample_set,
            os.path.join(self.scratch, 'test_output.xlsx'),
            'xls',
            2,
            num_otus
        )

    # @unittest.skip('x')
    def test_upload_adams_ENIGMA_samples(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "SampleMetaData.tsv")
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 1,
            'set_name': 'Enigma_test',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        self.verify_samples(
            ret['sample_set'],
            os.path.join(self.curr_dir, 'data', 'compare_to_ENIGMA.json')
        )

    # @unittest.skip('x')
    def test_upload_jon_marcs_ENIGMA_samples(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "samples_merged.tsv")
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 1,
            'set_name': 'Enigma_test_2',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        self.verify_samples(
            ret['sample_set'],
            os.path.join(self.curr_dir, 'data', 'compare_to_ENIGMA_2.json')
        )

    # @unittest.skip('x')
    def test_change_acls(self):
        self.maxDiff = None
        params = {
            'new_users': [
                "eapearson"
            ],
            'is_admin': 1,
            'is_reader': 0,
            'is_writer': 0,
            'sample_set_ref': self.sample_set_ref,
        }
        ret = self.serviceImpl.update_sample_set_acls(self.ctx, params)[0]
        print(ret)

    # @unittest.skip('x')
    def test_import_with_existing(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "samples_merged.tsv")
        params = {
            'sample_set_ref': self.sample_set_ref,
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "ENIGMA",
            'header_row_index': 1,
            'set_name': 'Enigma_test_2',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 1
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]

    # @unittest.skip('x')
    def test_kbase_format(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, 'data', 'kbase_style_samples.tsv')
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "KBASE",
            'header_row_index': 1,
            'set_name': 'kbase_test_1',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 0
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]

    # @unittest.skip('x')
    def test_id_field_argument(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, 'data', 'test_id_field.tsv')

        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "KBASE",
            'header_row_index': 1,
            'set_name': 'kbase_test_1',
            'description': "this is a test sample set.",
            'output_format': "",
            'otu_prefix': 'OTU',
            'sample_set_ref': None,
            'taxonomy_source': 'n/a',
            "incl_input_in_output": 1,
            "incl_seq": 0,
            "num_otus": 20,
            'id_field': "Jumbo Name of the Day"
        }
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]

    # @unittest.skip('x')
    def test_error_state(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, "data", "error_file.tsv")

        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "KBASE",
            'header_row_index': 1,
            'set_name': 'kbase_error_test',
            'description': "this is a test sample set.",
            'output_format': "",
            'otu_prefix': 'OTU',
            'sample_set_ref': None,
            'taxonomy_source': 'n/a',
            "incl_input_in_output": 1,
            "incl_seq": 0,
            "num_otus": 20,
        }
        with self.assertRaises(RuntimeError):
            ret = self.serviceImpl.import_samples(self.ctx, params)[0]

    # @unittest.skip('x')
    def test_workspace_acls_on_import(self):
        self.maxDiff = None
        sample_file = os.path.join(self.curr_dir, 'data', 'kbase_style_samples.tsv')
        params = {
            'workspace_name': self.wsName,
            'workspace_id': self.wsID,
            'sample_file': sample_file,
            'file_format': "KBASE",
            'header_row_index': 1,
            'set_name': 'kbase_test_1',
            'description': "this is a test sample set.",
            'output_format': "",
            "incl_input_in_output": 0,
            "share_within_workspace": 1
        }
        # add new user to permissions for test
        self.wsClient.set_permissions({
            "id": self.wsID,
            "new_permission": "w",
            "users": ["jrbolton"]
        })
        ret = self.serviceImpl.import_samples(self.ctx, params)[0]
        # get WS perms
        perms = self.wsClient.get_permissions_mass({
            'workspaces': [{'id': self.wsID}]
        })['perms'][0]
        sample_id = ret['sample_set']['samples'][0]['id']
        payload = {
            "method": "SampleService.get_sample_acls",
            "id": str(uuid.uuid4()),
            "params": [{"id": sample_id}],
            "version": "1.1"
        }
        resp = requests.get(url=self.sample_url, data=json.dumps(payload), headers={"Authorization": self.ctx['token']})
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
        self.assertEqual(resp_data, perms, msg=f"{resp_data} and {perms} are not the same.")
