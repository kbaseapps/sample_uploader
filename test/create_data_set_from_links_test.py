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
        cls.ws_url = cls.cfg['workspace-url']
        cls.ws_client = Workspace(cls.ws_url, token=token)
        cls.service_impl = sample_uploader(cls.cfg)
        cls.curr_dir = os.path.dirname(os.path.realpath(__file__))
        cls.scratch = cls.cfg['scratch']
        cls.wiz_url = cls.cfg['srv-wiz-url']
        cls.sample_url = cls.cfg['kbase-endpoint'] + '/sampleservice'
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
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
        # probably the actual upa
        cls.sample_set_ref = ret['sample_set_ref']

        cls.sample_name_1 = cls.sample_set['samples'][0]['name']
        cls.sample_name_2 = cls.sample_set['samples'][1]['name']
        cls.sample_name_3 = cls.sample_set['samples'][2]['name']

        # reference data set upas
        # TODO make a bunch of copies of these objects
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
            # cls.ReadLinkingTestSampleSet = '59862/11/1'  # SampleSet
            cls.rhodo_art_jgi_reads = '67096/8/4'  # paired
            cls.rhodobacter_art_q20_int_PE_reads = '67096/3/1'  # paired
            cls.rhodobacter_art_q50_SE_reads = '67096/2/1'  # single
            cls.test_genome = '67096/6/1'
            # cls.test_genome_name = 'Acaryochloris_marina_MBIC11017'
            cls.test_genome_2 = '67096/5/8'
            cls.test_assembly_1 = '67096/13/1'
            # cls.test_genome_2_name = 'test do i have to keep the same name?'
            # cls.test_genome = '59862/27/1'
            # cls.test_genome_name = 'test_Genome'
            # cls.test_assembly_SE_reads = '59862/26/1'
            # cls.test_assembly_SE_reads_name = 'single_end_kbassy'
            # cls.test_assembly_PE_reads = '59862/25/1'
            # cls.test_assembly_PE_reads_name = 'kbassy_roo_f'
            # cls.test_AMA_genome = '59862/28/1'
            cls.target_wsID = 67096

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
            'object_type': 'KBaseFile.SingleEndLibrary',
            'output_object_name': 'test_data_links_reads',
            'collision_resolution': 'newest',
            'description': 'filtered reads set bing bong'
        })

        meta = ret.get('set_info')[-1]

        self.assertEquals(int(meta.get('item_count')), 1)
        self.assertEquals(meta.get('description'), 'filtered reads set bing bong')
        self.assertEquals(ret['set_info'][6], self.target_wsID)
        self.assertIn('KBaseSets.ReadsSet', ret['set_info'][2])

    def test_create_data_set_genome_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'object_type': 'KBaseGenomes.Genome',
            'output_object_name': 'test_data_links_genomes',
            'collision_resolution': 'newest',
            'description': 'created genomes set woo hoo'
        })

        meta = ret.get('set_info')[-1]

        self.assertEquals(int(meta.get('item_count')), 2)
        self.assertEquals(meta.get('description'), 'created genomes set woo hoo')
        self.assertEquals(ret['set_info'][6], self.target_wsID)
        self.assertIn('KBaseSets.GenomeSet', ret['set_info'][2])

    def test_create_data_set_legacy_genome_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'object_type': 'KBaseGenomes.Genome__legacy',
            'output_object_name': 'test_data_links_legacy_genomes',
            'collision_resolution': 'newest',
            'description': 'old skool legacy genomes set'
        })

        meta = ret.get('set_info')[-1]

        # TODO: figure out why metadata doesn't get saved, its just an empty object even
        # if 'metadata' field is added to "elements" in legacy genome set
        # self.assertEquals(int(meta.get('item_count')), 2)
        # self.assertEquals(meta.get('description'), 'old skool legacy genomes set'),
        self.assertEquals(ret['set_info'][6], self.target_wsID)
        self.assertIn('KBaseSearch.GenomeSet', ret['set_info'][2])

    def test_create_data_set_assembly_links(self):
        ret = self.service_impl.create_data_set_from_links(self.ctx, {
            'sample_set_refs': [self.sample_set_ref],
            'object_type': 'KBaseGenomeAnnotations.Assembly',
            'output_object_name': 'test_data_links_assembly',
            'collision_resolution': 'newest',
            'description': 'assembly set!! AAAA!!'
        })

        meta = ret.get('set_info')[-1]

        self.assertEquals(int(meta.get('item_count')), 1)
        self.assertEquals(meta.get('description'), 'assembly set!! AAAA!!')
        self.assertEquals(ret['set_info'][6], self.target_wsID)
        self.assertIn('KBaseSets.AssemblySet', ret['set_info'][2])
