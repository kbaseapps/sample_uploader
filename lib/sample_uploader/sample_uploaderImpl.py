# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os
import uuid
import shutil
import csv
import datetime

from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.SampleServiceClient import SampleService
from installed_clients.sample_search_apiClient import sample_search_api
from installed_clients.WorkspaceClient import Workspace as workspaceService
from installed_clients.SetAPIClient import SetAPI
from sample_uploader.utils.exporter import sample_set_to_output
from sample_uploader.utils.importer import import_samples_from_file, find_header_row
from sample_uploader.utils.mappings import SESAR_mappings, ENIGMA_mappings, aliases
from sample_uploader.utils.sample_utils import (
    sample_set_to_OTU_sheet,
    update_acls,
    build_links,
    get_data_links_from_ss
)
from sample_uploader.utils.sesar_api import igsns_to_csv
from sample_uploader.utils.ncbi_api import ncbi_samples_to_csv
from sample_uploader.utils.misc_utils import get_workspace_user_perms
from sample_uploader.utils.misc_utils import error_ui as _error_ui
from sample_uploader.utils.parsing_utils import upload_key_format as _upload_key_format
#END_HEADER


class sample_uploader:
    '''
    Module Name:
    sample_uploader

    Module Description:
    A KBase module: sample_uploader
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "1.1.1"
    GIT_URL = "git@github.com:charleshtrenholm/sample_uploader.git"
    GIT_COMMIT_HASH = "20e60df2dfa54b90ba25dad4110cea5d0123754e"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.token = os.environ['KB_AUTH_TOKEN']
        self.workspace_url = config['workspace-url']
        self.scratch = config['scratch']
        # janky, but works for now
        self.sw_url = config.get('kbase-endpoint') + '/service_wizard'
        self.sample_url = config.get('kbase-endpoint') + '/sampleservice'
        self.dfu = DataFileUtil(url=self.callback_url)
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        self.sample_url = config.get('kbase-endpoint') + '/sampleservice'
        self.wsClient = workspaceService(self.workspace_url, token=self.token)
        #END_CONSTRUCTOR
        pass


    def import_samples(self, ctx, params):
        """
        :param params: instance of type "ImportSampleInputs" -> structure:
           parameter "sample_set_ref" of String, parameter "sample_file" of
           String, parameter "workspace_name" of String, parameter
           "workspace_id" of Long, parameter "file_format" of String,
           parameter "description" of String, parameter "set_name" of String,
           parameter "header_row_index" of Long, parameter "name_field" of
           String, parameter "output_format" of String, parameter
           "taxonomy_source" of String, parameter "num_otus" of Long,
           parameter "incl_seq" of Long, parameter "otu_prefix" of String,
           parameter "share_within_workspace" of Long, parameter
           "prevalidate" of Long, parameter "incl_input_in_output" of Long,
           parameter "ignore_warnings" of Long, parameter
           "keep_existing_samples" of Long, parameter "propagate_links" of
           Long
        :returns: instance of type "ImportSampleOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String, parameter "sample_set_ref" of
           String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN import_samples
        print(f"Beginning sample import with following parameters:")
        print(f"params -- {params}")
        sample_set = {"samples": []}
        # Check if we have an existing Sample Set as input
        # if so, download
        if params.get('sample_set_ref'):
            ret = self.dfu.get_objects({'object_refs': [params['sample_set_ref']]})['data'][0]
            sample_set = ret['data']
            if params.get('set_name'):
                set_name = params.get('set_name')
            else:
                set_name = ret['info'][1]
            save_ws_id = params['sample_set_ref'].split('/')[0]
        else:
            if not params.get('set_name'):
                raise ValueError(f"Sample set name required, when new SampleSet object is created.")
            set_name = params['set_name']
            save_ws_id = params.get('workspace_id')
        if params.get('header_row_index'):
            header_row_index = int(params["header_row_index"]) - 1
        else:
            header_row_index = find_header_row(params.get('sample_file'),
                                               params.get('file_format'))

        username = ctx['user_id']

        if str(params.get('file_format')).lower() not in ['enigma', 'sesar', 'kbase']:
            raise ValueError(f"Only SESAR, ENIGMA, and KBase formats are currently supported for importing samples. "
                             f"File of format {params.get('file_format')} not supported.")
        mappings = {'enigma': ENIGMA_mappings, 'sesar': SESAR_mappings, 'kbase': {}}

        sample_set, has_unignored_errors, errors, sample_data_json = import_samples_from_file(
            params,
            self.sample_url,
            self.workspace_url,
            self.callback_url,
            username,
            ctx['token'],
            mappings[str(params.get('file_format')).lower()].get('groups', []),
            mappings[str(params.get('file_format')).lower()].get('date_columns', []),
            mappings[str(params.get('file_format')).lower()].get('column_unit_regex', []),
            sample_set,
            header_row_index,
            aliases.get(params.get('file_format').lower(), {})
        )

        file_links = []
        new_data_links = []
        sample_set_ref = None

        # create UI to display the errors clearly
        html_link = _error_ui(errors, sample_data_json, has_unignored_errors, self.scratch)

        if not has_unignored_errors:
            # only save object if there are no errors
            obj_info = self.dfu.save_objects({
                'id': save_ws_id,
                'objects': [{
                    "name": set_name,
                    "type": "KBaseSets.SampleSet",
                    "data": sample_set
                }]
            })[0]

            sample_set_ref = '/'.join([str(obj_info[6]), str(obj_info[0]), str(obj_info[4])])
            sample_file_name = os.path.basename(params['sample_file']).split('.')[0] + '_OTU'

            # create a data link between each sample and the sampleset
            ss = SampleService(self.sample_url)
            for idx, sample_info in enumerate(sample_set['samples']):
                sample_id = sample_info['id']
                version = sample_info['version']
                sample = ss.get_sample({
                    'id': sample_id,
                    'version': version,
                })
                ret = ss.create_data_link(
                    dict(
                        upa=sample_set_ref,
                        id=sample_id,
                        dataid='samples/{}'.format(idx),
                        version=version,
                        node=sample['node_tree'][0]['id'],
                        update=1,
                    )
                )
                new_data_links.append(ret)

            # -- Format outputs below --
            # if output file format specified, add one to output
            if params.get('output_format') in ['csv', 'xls']:
                otu_path = sample_set_to_OTU_sheet(
                    sample_set,
                    sample_file_name,
                    self.scratch,
                    params
                )
                file_links.append({
                    'path': otu_path,
                    'name': os.path.basename(otu_path),
                    'label': "OTU template file",
                    'description': "file with each column containing the assigned sample_id and sample "
                                   "name of each saved sample. Intended for uploading OTU data."
                })

        if params.get('incl_input_in_output'):
            sample_file = params.get('sample_file')
            if not os.path.isfile(sample_file):
                # try prepending '/staging/' to file and check then
                if os.path.isfile(os.path.join('/staging', sample_file)):
                    sample_file = os.path.join('/staging', sample_file)
                else:
                    raise ValueError(f"Input file {sample_file} does not exist.")
            sample_file_copy = os.path.join(self.scratch, os.path.basename(sample_file))
            shutil.copy(sample_file, sample_file_copy)
            file_links.append({
                "path": sample_file_copy,
                "name": os.path.basename(sample_file_copy),
                "label": "Input Sample file",
                "description": "Input file provided to create the sample set."
            })

        # create report
        report_client = KBaseReport(self.callback_url)
        report_data = {
            'report_object_name': "SampleSet_import_report_" + str(uuid.uuid4()),
            'workspace_name': params['workspace_name']
        }
        if file_links:
            report_data['file_links'] = file_links
        if sample_set_ref:
            report_data['message'] = f"SampleSet object named \"{set_name}\" imported."
            report_data['objects_created'] = [{'ref': sample_set_ref}]

        if html_link:
            report_data['html_links'] =  [{
                'path': html_link,
                'name': 'index.html',
                'description': 'HTML Report for Sample Uploader'
            }]
            report_data['direct_html_link_index'] = 0
        report_info = report_client.create_extended_report(report_data)
        output = {
            'report_ref': report_info['ref'],
            'report_name': report_info['name'],
            'sample_set': sample_set,
            'sample_set_ref': sample_set_ref,
            'errors': errors,
            'links': new_data_links
        }
        #END import_samples

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method import_samples return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def import_samples_from_IGSN(self, ctx, params):
        """
        :param params: instance of type "ImportExternalSampleInputs" ->
           structure: parameter "sample_set_ref" of String, parameter
           "external_ids" of list of String, parameter "workspace_name" of
           String, parameter "workspace_id" of Long, parameter "description"
           of String, parameter "set_name" of String, parameter
           "output_format" of String, parameter "taxonomy_source" of String,
           parameter "num_otus" of Long, parameter "incl_seq" of Long,
           parameter "otu_prefix" of String, parameter
           "share_within_workspace" of Long, parameter "prevalidate" of Long,
           parameter "incl_input_in_output" of Long
        :returns: instance of type "ImportSampleOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String, parameter "sample_set_ref" of
           String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN import_samples_from_IGSN

        igsns = params.get('external_ids')
        if not igsns:
            raise ValueError('Please provide IGSNs')

        if isinstance(igsns, str):
            if igsns.isalnum():
                # single igsn given e.g. 'IEAWH0001'
                igsns = [igsns]
            else:
                # multiple igsn given e.g. 'IEAWH0001, GEE0000O4' or 'IEAWH0001; GEE0000O4'
                delimiter = csv.Sniffer().sniff(igsns).delimiter
                igsns = [x.strip() for x in igsns.split(delimiter)]

        logging.info('Start importing samples from IGSNs: {}'.format(igsns))

        sample_file_name = 'igsn_sample_{}.csv'.format(str(uuid.uuid4()))
        sample_file_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(sample_file_dir)
        sample_file = os.path.join(sample_file_dir, sample_file_name)

        igsns_to_csv(igsns, sample_file)

        params['sample_file'] = sample_file
        params['file_format'] = 'sesar'
        params["header_row_index"] = 2

        output = self.import_samples(ctx, params)[0]
        #END import_samples_from_IGSN

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method import_samples_from_IGSN return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def import_samples_from_NCBI(self, ctx, params):
        """
        :param params: instance of type "ImportExternalSampleInputs" ->
           structure: parameter "sample_set_ref" of String, parameter
           "external_ids" of list of String, parameter "workspace_name" of
           String, parameter "workspace_id" of Long, parameter "description"
           of String, parameter "set_name" of String, parameter
           "output_format" of String, parameter "taxonomy_source" of String,
           parameter "num_otus" of Long, parameter "incl_seq" of Long,
           parameter "otu_prefix" of String, parameter
           "share_within_workspace" of Long, parameter "prevalidate" of Long,
           parameter "incl_input_in_output" of Long
        :returns: instance of type "ImportSampleOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String, parameter "sample_set_ref" of
           String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN import_samples_from_NCBI
        ncbi_sample_ids = params.get('external_ids')
        if not ncbi_sample_ids:
            raise ValueError('Please provide NCBI sample IDs')

        if isinstance(ncbi_sample_ids, str):
            if ncbi_sample_ids.isalnum():
                # single igsn given e.g. 'SAMN03166112'
                ncbi_sample_ids = [ncbi_sample_ids]
            else:
                # multiple igsn given e.g. 'SAMN03166112', 'SAMN04383980'
                delimiter = csv.Sniffer().sniff(ncbi_sample_ids).delimiter
                ncbi_sample_ids = [x.strip() for x in ncbi_sample_ids.split(delimiter)]

        logging.info('Start importing samples from NCBI: {}'.format(ncbi_sample_ids))

        sample_file_name = 'ncbi_sample_{}.csv'.format(str(uuid.uuid4()))
        sample_file_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(sample_file_dir)
        sample_file = os.path.join(sample_file_dir, sample_file_name)

        ncbi_samples_to_csv(ncbi_sample_ids, sample_file)

        params['sample_file'] = sample_file
        params['file_format'] = 'kbase'

        output = self.import_samples(ctx, params)[0]
        #END import_samples_from_NCBI

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method import_samples_from_NCBI return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def generate_OTU_sheet(self, ctx, params):
        """
        :param params: instance of type "GenerateOTUSheetParams" (Generate a
           customized OTU worksheet using a SampleSet input to generate the
           appropriate columns.) -> structure: parameter "workspace_name" of
           String, parameter "workspace_id" of Long, parameter
           "sample_set_ref" of String, parameter "output_name" of String,
           parameter "output_format" of String, parameter "num_otus" of Long,
           parameter "taxonomy_source" of String, parameter "incl_seq" of
           Long, parameter "otu_prefix" of String
        :returns: instance of type "GenerateOTUSheetOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN generate_OTU_sheet
        # first we download sampleset
        sample_set_ref = params.get('sample_set_ref')
        ret = self.dfu.get_objects({'object_refs': [sample_set_ref]})['data'][0]
        sample_set = ret['data']
        if params.get('output_name'):
            output_name = params.get('output_name')
        else:
            # if output_name not specified use name of sample_set as output + "_OTUs"
            output_name = ret['info'][1] + "_OTUs"
        otu_path = sample_set_to_OTU_sheet(
            sample_set,
            output_name,
            self.scratch,
            params
        )
        report_client = KBaseReport(self.callback_url)
        report_name = "Generate_OTU_sheet_report_" + str(uuid.uuid4())
        report_info = report_client.create_extended_report({
            'file_links': [{
                'path': otu_path,
                'name': os.path.basename(otu_path),
                'label': "CSV with headers for OTU",
                'description': "CSV file with each column containing the assigned sample_id and sample "
                               "name of each saved sample. Intended for uploading OTU data."
            }],
            'report_object_name': report_name,
            'workspace_name': params['workspace_name']
        })
        output = {
            'report_ref': report_info['ref'],
            'report_name': report_info['name'],
        }

        #END generate_OTU_sheet

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method generate_OTU_sheet return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def update_sample_set_acls(self, ctx, params):
        """
        :param params: instance of type "update_sample_set_acls_params" ->
           structure: parameter "workspace_name" of String, parameter
           "workspace_id" of Long, parameter "sample_set_ref" of String,
           parameter "new_users" of list of String, parameter "is_reader" of
           Long, parameter "is_writer" of Long, parameter "is_admin" of Long,
           parameter "is_none" of Long, parameter "share_within_workspace" of
           Long
        :returns: instance of type "update_sample_set_acls_output" ->
           structure: parameter "status" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN update_sample_set_acls

        # first get sample_set object
        sample_set_ref = params.get('sample_set_ref')
        ret = self.dfu.get_objects({'object_refs': [sample_set_ref]})['data'][0]
        sample_set = ret['data']

        acls = {
            'read': [],
            'write': [],
            'admin': [],
            'remove': []
        }

        if params.get('share_within_workspace'):
            acls = get_workspace_user_perms(self.workspace_url, params.get('workspace_id'), ctx['token'], ctx['user_id'], acls)

        for new_user in params.get('new_users'):
            if params.get('is_admin'):
                acls['admin'].append(new_user)
            elif params.get('is_writer'):
                acls['write'].append(new_user)
            elif params.get('is_reader'):
                acls['read'].append(new_user)
            elif params.get('is_none'):
                acls['remove'].append(new_user)

        for sample in sample_set['samples']:
            sample_id = sample['id']
            status = update_acls(self.sample_url, sample_id, acls, ctx['token'])
        output = {"status": status}
        #END update_sample_set_acls

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method update_sample_set_acls return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def export_samples(self, ctx, params):
        """
        :param params: instance of type "ExportParams" (export function for
           samples) -> structure: parameter "input_ref" of String, parameter
           "file_format" of String
        :returns: instance of type "ExportOutput" -> structure: parameter
           "shock_id" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN export_samples
        if not params.get('input_ref'):
            raise ValueError(f"variable input_ref required")
        sample_set_ref = params.get('input_ref')
        output_file_format = params.get('file_format', 'sesar')

        ret = self.dfu.get_objects({'object_refs': [sample_set_ref]})['data'][0]
        sample_set = ret['data']
        sample_set_name = ret['info'][1]

        export_package_dir = os.path.join(self.scratch, "output")
        if not os.path.isdir(export_package_dir):
            os.mkdir(export_package_dir)
        output_file = os.path.join(export_package_dir, '_'.join(sample_set_name.split()) + ".csv")

        sample_set_to_output(sample_set, self.sample_url, ctx['token'], output_file, output_file_format)

        # package it up
        package_details = self.dfu.package_for_download({
            'file_path': export_package_dir,
            'ws_refs': [params['input_ref']]
        })

        output = {
            'shock_id': package_details['shock_id'],
            'result_dir': export_package_dir
        }
        #END export_samples

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method export_samples return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def link_samples(self, ctx, params):
        """
        :param params: instance of type "LinkObjsParams" -> structure:
           parameter "workspace_name" of String, parameter "workspace_id" of
           String, parameter "sample_set_ref" of String, parameter "links" of
           list of type "ObjsLink" (Create links between samples and other
           workspace objects. currently support:
           KBaseFile.PairedEndLibrary/SingleEndLibrary,
           KBaseAssembly.PairedEndLibrary/SingleEndLibrary,
           KBaseGenomes.Genome, KBaseMetagenomes.AnnotatedMetagenomeAssembly,
           KBaseMetagenomes.BinnedContigs KBaseGenomeAnnotations.Assembly,
           KBaseSearch.GenomeSet, KBaseSets.AssemblySet, KBaseSets.GenomeSet)
           -> structure: parameter "sample_name" of String, parameter
           "obj_ref" of String
        :returns: instance of type "LinkObjsOutput" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String,
           parameter "links" of list of unspecified object
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN link_samples
        logging.info(params)

        ss = SampleService(self.sample_url)

        sample_set_ref = params.get('sample_set_ref')
        if not sample_set_ref:
            raise ValueError('Missing sample set object')

        sample_set_obj = self.dfu.get_objects({'object_refs': [sample_set_ref]})['data'][0]['data']
        sample_name_2_info = {d['name']: d for d in sample_set_obj['samples']}

        links = [(d['sample_name'][0], d['obj_ref']) for d in params['links']]

        accepted_types = ["KBaseFile.SingleEndLibrary",
                          "KBaseFile.PairedEndLibrary",
                          "KBaseAssembly.SingleEndLibrary",
                          "KBaseAssembly.PairedEndLibrary",
                          "KBaseGenomes.Genome",
                          "KBaseMetagenomes.AnnotatedMetagenomeAssembly",
                          "KBaseMetagenomes.BinnedContigs",
                          "KBaseGenomeAnnotations.Assembly",
                          "KBaseSearch.GenomeSet",
                          "KBaseSets.AssemblySet",
                          "KBaseSets.GenomeSet"]

        new_data_links = []
        for sample_name, obj_ref in links:
            obj_type = self.wsClient.get_object_info3({
                'objects': [{"ref": obj_ref}], 'includeMetadata': 0})["infos"][0][2].split('-')[0]
            if obj_type not in accepted_types:
                raise ValueError('Unsupported object type [{}]. Please provide one of {}'.format(
                    obj_type, accepted_types))
            sample_id = sample_name_2_info[sample_name]['id']
            version = sample_name_2_info[sample_name]['version']
            idx = list(sample_name_2_info.keys()).index(sample_name)

            sample = ss.get_sample({
                'id': sample_id,
                'version': version,
            })
            ret = ss.create_data_link(
                dict(
                    upa=obj_ref,
                    id=sample_id,
                    dataid='samples/{}'.format(idx),
                    version=version,
                    node=sample['node_tree'][0]['id'],
                    update=1,
                )
            )
            new_data_links.append(ret)

        new_links = [d['new_link'] for d in new_data_links]
        sample_names_out = [link['node'] for link in new_links]
        report_msg = 'Links created for samples:\n{}'.format('\n'.join(sample_names_out))
        report_client = KBaseReport(self.callback_url)
        report_info = report_client.create_extended_report({
            'message': report_msg,
            'workspace_name': params['workspace_name'],
        })
        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref'],
            'links': new_data_links,
        }
        #END link_samples

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method link_samples return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def batch_link_samples(self, ctx, params):
        """
        :param params: instance of type "BatchLinkObjsParams"
           (input_staging_file_path: tsv or csv file with sample_name and
           object_name headers) -> structure: parameter "workspace_name" of
           String, parameter "workspace_id" of String, parameter
           "sample_set_ref" of String, parameter "input_staging_file_path" of
           String
        :returns: instance of type "LinkObjsOutput" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String,
           parameter "links" of list of unspecified object
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN batch_link_samples
        logging.info('start batch linking samples\n{}'.format(params))

        links = build_links(params.get('input_staging_file_path'),
                            self.callback_url,
                            self.workspace_url,
                            params.get('workspace_id'),
                            self.token)
        params['links'] = links

        output = self.link_samples(ctx, params)[0]
        #END batch_link_samples

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method batch_link_samples return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def filter_samplesets(self, ctx, params):
        """
        :param params: instance of type "FilterSampleSetsParams" ->
           structure: parameter "workspace_name" of String, parameter
           "workspace_id" of String, parameter "out_sample_set_name" of
           String, parameter "sample_set_ref" of list of String, parameter
           "filter_conditions" of list of type "FilterCondition" (Filter
           SampleSets) -> structure: parameter "metadata_field" of String,
           parameter "comparison_operator" of String, parameter "value" of
           String, parameter "logical_operator" of String
        :returns: instance of type "FilterSampleSetsOutput" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN filter_samplesets
        samples = []
        for sample_set in self.dfu.get_objects({'object_refs': params['sample_set_ref']})['data']:
            samples.extend(sample_set['data']['samples'])
        sample_ids = [{'id': sample['id'], 'version':sample['version']} for sample in samples]

        filter_conditions = []
        for i, condition in enumerate(params['filter_conditions']):
            metadata_values = []
            if (condition['comparison_operator'].strip().lower() not in ["in", "not in"]):
                if (len(condition['value']) < 1):
                    raise ValueError('Filter condition #{} has no filter value'.format(i + 1))
                metadata_values = [condition['value']]
            else:
                metadata_values = [v.strip() for v in condition['value'].split(", ")]
                if (len(metadata_values) < 1):
                    raise ValueError('Filter condition #{} has no filter values'.format(i + 1))

            metadata_field = _upload_key_format(condition['metadata_field'])
            if (metadata_field is None or len(metadata_field) < 1):
                raise ValueError('Filter condition #{} has no specified Column/Key'.format(i + 1))

            comparison_operator = condition['comparison_operator']
            if (comparison_operator is None or len(comparison_operator) < 1):
                raise ValueError(
                    'Filter condition #{} has no specified comparison operator'.format(i + 1))

            logical_operator = condition['logical_operator']
            if (logical_operator is None or len(logical_operator) < 1):
                raise ValueError(
                    'Filter condition #{} has no specified logical operator'.format(i + 1))

            filter_conditions.append({
                'metadata_field': metadata_field,
                'comparison_operator': comparison_operator,
                'metadata_values': metadata_values,
                'logical_operator': logical_operator
            })

        sample_search_api_request = {
            'sample_ids': sample_ids,
            'filter_conditions': filter_conditions
        }

        sample_search_api_response = sample_search_api(
            url=self.sw_url, service_ver='dev').filter_samples(sample_search_api_request)

        samples_to_keep = set(sample_id['id']
                              for sample_id in sample_search_api_response['sample_ids'])

        sample_set = {
            'samples': [sample for sample in samples if sample['id'] in samples_to_keep],
            "description": "Generated with the Sample Set Editor"
        }

        conditions_summary = ''
        for i, condition in enumerate(filter_conditions):
            conditions_summary += '"{}" {} "{}" {}'.format(
                condition['metadata_field'],
                condition['comparison_operator'],
                condition['metadata_values'],
                (
                    'AND ' if condition['logical_operator'].upper() == 'AND' else 'OR '
                ) if i != len(filter_conditions) - 1 else '')

        obj_info = self.dfu.save_objects({
            'id': params['workspace_id'],
            'objects': [{
                "name": params['out_sample_set_name'],
                "type": "KBaseSets.SampleSet",
                "data": sample_set
            }]
        })

        report_client = KBaseReport(self.callback_url)
        sample_set_refs = [f"{i[6]}/{i[0]}/{i[4]}" for i in obj_info]
        report_info = report_client.create_extended_report({
            'objects_created': [
                {
                    'ref': ref
                } for ref in sample_set_refs
            ],
            'message': f"SampleSet object named \"{params['out_sample_set_name']}\" \
created with condition(s): {conditions_summary}",
            'workspace_name': params['workspace_name']
        })
        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref'],
            'sample_set': sample_set,
            'sample_set_refs': sample_set_refs
        }
        #END filter_samplesets

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method filter_samplesets return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def get_sampleset_meta(self, ctx, params):
        """
        :param params: instance of type "GetSamplesetMetaParams" (Get list of
           metadata keys/columns from a given list of samplesets. Used to
           populate filter_sampleset dynamic dropdown with valid options from
           a given list of samples.) -> structure: parameter
           "sample_set_refs" of list of String
        :returns: instance of list of String
        """
        # ctx is the context object
        # return variables are: results
        #BEGIN get_sampleset_meta
        samples = []
        for sample_set in self.dfu.get_objects({'object_refs': params['sample_set_refs']})['data']:
            samples.extend(sample_set['data']['samples'])
        try:
            sample_ids = [{'id': sample['id'], 'version':sample['version']} for sample in samples]
        except KeyError as e:
            raise ValueError(
                f'Invalid sampleset ref - sample in dataset missing the "{str(e)}" field'
            )
        sample_search = sample_search_api(url=self.sw_url, service_ver="dev")
        results = sample_search.get_sampleset_meta({
            'sample_ids': sample_ids
        })['results']

        #END get_sampleset_meta

        # At some point might do deeper type checking...
        if not isinstance(results, list):
            raise ValueError('Method get_sampleset_meta return value ' +
                             'results is not type list as required.')
        # return the results
        return [results]

    def create_data_set_from_links(self, ctx, params):
        """
        :param params: instance of type "CreateDataSetFromLinksParams" ->
           structure: parameter "description" of String, parameter
           "sample_set_refs" of list of String, parameter "object_type" of
           String, parameter "output_object_name" of String, parameter
           "collision_resolution" of String, parameter "ws_id" of Int
        :returns: instance of type "CreateDataSetFromLinksResults" ->
           structure: parameter "set_ref" of String, parameter "ws_upa" of
           String, parameter "name" of String
        """
        # ctx is the context object
        # return variables are: results
        #BEGIN create_data_set_from_links
        sample_service = SampleService(self.sample_url)
        set_api = SetAPI(self.callback_url)
        now = round(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() * 1000)

        try:
            object_type = params['object_type']
        except KeyError:
            raise ValueError('input object type must be specified.')

        # list of supported KBase types mapped to their set counterparts
        # TODO: Theres' got to be a snazzier way to check which type goes into a set type
        # maybe this could be a SetAPI feature
        types_map = {
            'KBaseFile.SingleEndLibrary': 'KBaseSets.ReadsSet',
            'KBaseFile.PairedEndLibrary': 'KBaseSets.ReadsSet',
            'KBaseGenomes.Genome': 'KBaseSets.GenomeSet',
            'KBaseGenomes.Genome__legacy': 'KBaseSearch.GenomeSet',
            'KBaseGenomeAnnotations.Assembly': 'KBaseSets.AssemblySet'
        }

        if object_type not in types_map:
            raise ValueError(
                f'Creating a set from type {object_type} is not currently supported by this app.'
            )

        output_object_type = types_map[object_type]

        methods_map = {
            # TODO: handle case for legacy GenomeSet
            'KBaseSets.ReadsSet': set_api.save_reads_set_v1,
            'KBaseSets.GenomeSet': set_api.save_genome_set_v1,
            'KBaseSearch.GenomeSet': set_api.save_genome_set_v1,
            'KBaseSets.AssemblySet': set_api.save_assembly_set_v1
        }

        samples = []
        for sample_set in self.dfu.get_objects({'object_refs': params['sample_set_refs']})['data']:
            samples.extend(sample_set['data']['samples'])
        try:
            sample_ids = [{'id': sample['id'], 'version':sample['version']} for sample in samples]
        except KeyError as e:
            raise ValueError(
                f'Invalid sampleset ref - sample in dataset missing the "{str(e)}" field'
            )
        data_links = sample_service.get_data_links_from_sample_set({
            'effective_time': now,
            'sample_ids': sample_ids
        })

        ret = self.wsClient.get_object_info3({
            'objects': [{'ref': link['upa']} for link in data_links['links']]
        }).get('infos')

        data_objs = [r for r in ret if r[2].split('-')[0] in object_type]

        upas = [f"{i[6]}/{i[0]}/{i[4]}" for i in data_objs]

        set_obj = {
            'description': params['description'],
            'items': [{'ref': u} for u in upas],
        }

        save_data = {
            'workspace': params['ws_id'],
            'output_object_name': params['output_object_name'], # make sure you check all the params exist
            'data': set_obj
        }

        if object_type == 'KBaseGenomes.Genome__legacy':
            save_data['save_search_set'] = True
            set_obj['elements'] = {}
            for i, upa in enumerate(upas):
                element = {
                    'ref': upa,
                    # todo: check if this is the right metadata
                    'metadata': data_objs[i][-1] if data_objs[i][-1] is not None else {}
                }
                set_obj['elements'][upa] = element

        set_api_method = methods_map[output_object_type]

        result = set_api_method(save_data)

        # TODO: decide what return object should look like
        return result

        #END create_data_set_from_links

        # At some point might do deeper type checking...
        if not isinstance(results, dict):
            raise ValueError('Method create_data_set_from_links return value ' +
                             'results is not type dict as required.')
        # return the results
        return [results]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
