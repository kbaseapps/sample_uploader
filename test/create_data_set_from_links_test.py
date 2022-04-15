import os
import time
import unittest
from configparser import ConfigParser

from sample_uploader.sample_uploaderImpl import sample_uploader
from sample_uploader.sample_uploaderServer import MethodContext
from sample_uploader.authclient import KBaseAuth as _KBaseAuth
from installed_clients.WorkspaceClient import Workspace
from installed_clients.SampleServiceClient import SampleService
from installed_clients.SetAPIClient import SetAPI
from installed_clients.DataFileUtilClient import DataFileUtil

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
        cls.ws_url = cls.cfg['workspace-url']
        cls.ws_client = Workspace(cls.ws_url, token=token)
        cls.service_impl = sample_uploader(cls.cfg)
        cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.scratch = cls.cfg['scratch']
        cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/sampleservice'
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        cls.set_api_client = SetAPI(cls.callback_url)
        cls.dfu = DataFileUtil(url=cls.callback_url)
        suffix = int(time.time() * 1000)
        cls.ws_name = "test_sample_reads_linking_" + str(suffix)
        ret = cls.ws_client.create_workspace({'workspace': cls.ws_name})  # noqa
        cls.ws_id = ret[0]
        # TODO: probably should make a mock sample service
        cls.ss = SampleService(cls.sample_url, token=token)

        # create dummy data set
        sample_set_file = os.path.join(cls.curr_dir, 'data', 'fake_sample_data_set_links.csv')

        params = {
            'workspace_name': cls.ws_name,
            'workspace_id': cls.ws_id,
            'sample_file': sample_set_file,
            'file_format': "enigma",
            'header_row_index': 1,
            'set_name': 'create_data_links_from_set_set',
            'description': "this is a test sample set.",
            'output_format': "",
            'incl_input_in_output': 1,
            'share_within_workspace': 1,
            'ignore_warnings': 1
        }
        ret = cls.service_impl.import_samples(cls.ctx, params)[0]
        cls.sample_set = ret['sample_set']
        # first id of sample set - probably can remove this from class
        cls.sample_set_id = ret['sample_set']['samples'][0]['id']
        cls.sample_set_ref = ret['sample_set_ref']

        cls.sample_name_1 = cls.sample_set['samples'][0]['name']
        cls.sample_name_2 = cls.sample_set['samples'][1]['name']
        cls.sample_name_3 = cls.sample_set['samples'][2]['name']

        # reference data set upas
        # TODO make a bunch of copies of these objects
        if 'appdev' in cls.cfg['kbase-endpoint']:
            cls.ReadLinkingTestSampleSet = '66270/4/1'
            cls.rhodo_art_jgi_reads = '66270/14/1' # kbassy_roo_f, this is a SE lib in appdev
            cls.rhodobacter_art_q20_int_PE_reads = '66270/6/1'
            cls.rhodobacter_art_q50_SE_reads = '66270/7/2'
            cls.test_genome = '66270/16/1'
            cls.test_genome_2 = '66270/2/1'
            cls.test_assembly_1 = '66270/3/1'
            # test linking 2 versions of the same data set
            cls.collision_good_upa = '66270/7/2'
            cls.collision_bad_upa = '66270/7/1'
            cls.target_wsID = 66270
            cls.test_bad_collisions_type = 'KBaseFile.SingleEndLibrary'
            cls.test_collisions_expected_length = 1
        elif 'ci' in cls.cfg['kbase-endpoint']:
            # cls.ReadLinkingTestSampleSet = '59862/11/1'  # SampleSet
            cls.rhodo_art_jgi_reads = '67096/8/4'  # paired
            cls.rhodobacter_art_q20_int_PE_reads = '67096/3/1'  # paired
            cls.rhodobacter_art_q50_SE_reads = '67096/2/1'  # single
            cls.test_genome = '67096/6/1'
            cls.test_genome_2 = '67096/5/8'
            cls.test_assembly_1 = '67096/13/1'
            # test linking 2 versions of the same data set
            cls.collision_good_upa = '67096/8/4'
            cls.collision_bad_upa = '67096/8/2'
            cls.target_wsID = 67096
            cls.test_bad_collisions_type = 'KBaseFile.PairedEndLibrary'
            cls.test_collisions_expected_length = 2

        # input links data
        cls.links_in = [
            {'sample_name': [cls.sample_name_1], 'obj_ref': cls.rhodo_art_jgi_reads},
            {'sample_name': [cls.sample_name_2],
             'obj_ref': cls.rhodobacter_art_q20_int_PE_reads},
            {'sample_name': [cls.sample_name_3],
             'obj_ref': cls.rhodobacter_art_q50_SE_reads},
            {'sample_name': [cls.sample_name_1],
             'obj_ref': cls.test_genome},
             {'sample_name': [cls.sample_name_2],
             'obj_ref': cls.test_genome_2},
             {'sample_name': [cls.sample_name_1],
             'obj_ref': cls.test_assembly_1}
            # {'sample_name': [cls.sample_name_3], 'obj_ref': cls.test_genome},
            # {'sample_name': [cls.sample_name_3], 'obj_ref': cls.test_assembly_SE_reads},
            # {'sample_name': [cls.sample_name_3], 'obj_ref': cls.test_assembly_PE_reads},
            # {'sample_name': [cls.sample_name_3], 'obj_ref': cls.test_AMA_genome},
        ]

        cls.links_out = cls.service_impl.link_samples(
            cls.ctx, {
                'workspace_name': cls.ws_name,
                'sample_set_ref': cls.sample_set_ref,
                'links': cls.links_in,
            })

        # filtered sample set with reads
        # should only return 1 read object
        cls.filtered_sample_set_3 = cls.service_impl.filter_samplesets(cls.ctx, {
            'workspace_name': cls.ws_name,
            'workspace_id': cls.ws_id,
            'out_sample_set_name': "filtered_" + str(int(time.time() * 1000)),
            'sample_set_ref': [cls.sample_set_ref],
            'filter_conditions': [{
                'metadata_field': "enigma:area_name",
                'comparison_operator': "==",
                'value': "Area X",
                'logical_operator': "AND",
            }]
        })



        cls.filtered_sample_set_3_ref = cls.filtered_sample_set_3[0]['sample_set_refs'][0]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_name'):
            cls.ws_client.delete_workspace({'workspace': cls.ws_name})

    def test_create_data_set_reads_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.filtered_sample_set_3_ref],
            'collision_resolution': 'newest',
            'ws_id': self.target_wsID,
            'set_items': [{
                'object_type': 'KBaseFile.SingleEndLibrary',
                'output_object_name': 'test_data_links_reads',
                'description': 'filtered reads set bing bong'
            }]
        })
        meta = ret[0][0][-1]

        self.assertEquals(int(meta.get('item_count')), 1)
        self.assertEquals(meta.get('description'), 'filtered reads set bing bong')
        self.assertEquals(ret[0][0][6], self.target_wsID)
        self.assertIn('KBaseSets.ReadsSet', ret[0][0][2])

    def test_create_data_set_genome_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'collision_resolution': 'newest',
            'ws_id': self.target_wsID,
            'set_items': [{
                'object_type': 'KBaseGenomes.Genome',
                'output_object_name': 'test_data_links_genomes',
                'description': 'created genomes set woo hoo'
            }]
        })

        meta = ret[0][0][-1]

        self.assertEquals(int(meta.get('item_count')), 2)
        self.assertEquals(meta.get('description'), 'created genomes set woo hoo')
        self.assertEquals(ret[0][0][6], self.target_wsID)
        self.assertIn('KBaseSets.GenomeSet', ret[0][0][2])

    def test_create_data_set_legacy_genome_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'ws_id': self.target_wsID,
            'collision_resolution': 'newest',
            'set_items': [{
                'description': 'old skool legacy genomes set',
                'output_object_name': 'test_data_links_legacy_genomes',
                'object_type': 'KBaseGenomes.Genome__search'
            }]
        })

        meta = ret[0][0][-1]

        # TODO: figure out why metadata doesn't get saved, its just an empty object even
        # if 'metadata' field is added to "elements" in legacy genome set
        self.assertEquals(int(meta.get('item_count')), 2)
        self.assertEquals(meta.get('description'), 'old skool legacy genomes set'),
        self.assertEquals(ret[0][0][6], self.target_wsID)
        self.assertIn('KBaseSearch.GenomeSet', ret[0][0][2])

    def test_create_data_set_assembly_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'ws_id': self.target_wsID,
            'collision_resolution': 'newest',
            'set_items': [{
                'description': 'assembly set!! AAAA!!',
                'output_object_name': 'test_data_links_assembly',
                'object_type': 'KBaseGenomeAnnotations.Assembly'
            }]
        })

        meta = ret[0][0][-1]

        self.assertEquals(int(meta.get('item_count')), 1)
        self.assertEquals(meta.get('description'), 'assembly set!! AAAA!!')
        self.assertEquals(ret[0][0][6], self.target_wsID)
        self.assertIn('KBaseSets.AssemblySet', ret[0][0][2])

    def test_create_multiple_datasets(self):
        set_items = [{
            'object_type': 'KBaseGenomeAnnotations.Assembly',
            'output_object_name': 'data_set_1',
            'description': 'data set 1'
        },
                        {
            'object_type': 'KBaseFile.SingleEndLibrary',
            'output_object_name': 'data_set_2',
            'description': 'data set 2'
        },                {
            'object_type': 'KBaseFile.PairedEndLibrary',
            'output_object_name': 'data_set_3',
            'description': 'data set 3'
        }]
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'ws_id': self.target_wsID,
            'collision_resolution': 'newest',
            'set_items': set_items
        })

        self.assertEquals(len(ret[0]), 3)
        print('Return value ->', ret)
        expected_item_counts = [1,1,self.collisions_expected_length]
        expected_item_types = [
            'KBaseSets.AssemblySet',
            'KBaseSets.ReadsSet',
            'KBaseSets.ReadsSet'
        ]
        for i, item in enumerate(set_items):
            meta = ret[0][i][-1]
            self.assertEquals(int(meta.get('item_count')), expected_item_counts[i])
            self.assertEquals(meta.get('description'), set_items[i]['description'])
            self.assertEquals(ret[0][i][6], self.target_wsID)
            self.assertIn(expected_item_types[i], ret[0][i][2])

    def test_create_datasets_colliding_sample_versions(self):
        pass

    def test_create_dataset_colliding_data_link_versions(self):
        """
        Test that when given an opportunity to create a data set with conflicting versions
        of the same object, the app will only include the most recent version of the data
        object in question.
        """

        # create new sample set
        other_sample_set = self.service_impl.filter_samplesets(self.ctx, {
            'workspace_name': self.ws_name,
            'workspace_id': self.ws_id,
            'out_sample_set_name': "filtered_" + str(int(time.time() * 1000)),
            'sample_set_ref': [self.sample_set_ref],
            'filter_conditions': [{
                'metadata_field': "enigma:area_name",
                'comparison_operator': "==",
                'value': "Area X",
                'logical_operator': "AND",
            }]
        })

        other_sample_name = other_sample_set[0]['sample_set']['samples'][0]['name']
        # cls.sample_name_1 = cls.sample_set['samples'][0]['name']

        other_sample_set_ref = other_sample_set[0]['sample_set_refs'][0]

        # add link to older version of paired end library
        self.service_impl.link_samples(
            self.ctx, {
                'workspace_name': self.ws_name,
                'sample_set_ref': other_sample_set_ref,
                'links': [{
                    'sample_name': [other_sample_name],
                    'obj_ref': self.collision_bad_upa # compared to 67096/8/4
                }]
            })

        # create ReadsSet of all paired end libraries
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref, other_sample_set_ref],
            'ws_id': self.target_wsID,
            'collision_resolution': 'newest',
            'set_items': [{
                'description': 'this should only have 2 items linked to it! NOT 3!!',
                'output_object_name': 'test_collision_resolution_datalinks',
                'object_type': self.test_bad_collisions_type
            }]
        })

        meta = ret[0][0][-1]
        self.assertEquals(int(meta.get('item_count')),
                         self.test_collisions_expected_length)
        self.assertIn('KBaseSets.ReadsSet', ret[0][0][2])

        # get actual reads set and make sure the right things are in there
        reads_set = self.set_api_client.get_reads_set_v1({
            'ref': f"{ret[0][0][6]}/{ret[0][0][0]}/{ret[0][0][4]}",
            'include_set_ref_paths': 1
        })
        set_upas = [item['ref'] for item in reads_set['data']['items']]
        self.assertNotIn(self.collision_bad_upa, set_upas)
        self.assertIn(self.collision_good_upa, set_upas)
