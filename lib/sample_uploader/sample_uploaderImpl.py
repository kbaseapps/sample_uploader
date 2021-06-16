# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os
import json
import uuid
import shutil
import csv

from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.SampleServiceClient import SampleService
from sample_uploader.utils.exporter import sample_set_to_output
from sample_uploader.utils.importer import import_samples_from_file, find_header_row
from sample_uploader.utils.mappings import SESAR_mappings, ENIGMA_mappings, aliases
from sample_uploader.utils.sample_utils import (
    sample_set_to_OTU_sheet,
    update_acls,
    get_sample,
    format_sample_as_row,
)
from sample_uploader.utils.sesar_api import igsns_to_csv
from sample_uploader.utils.ncbi_api import ncbi_samples_to_csv
from sample_uploader.utils.misc_utils import get_workspace_user_perms
from sample_uploader.utils.misc_utils import error_ui as _error_ui
import pandas as pd
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
    VERSION = "0.0.22"
    GIT_URL = "git@github.com:Tianhao-Gu/sample_uploader.git"
    GIT_COMMIT_HASH = "4d4ed0b9fa6431230658800bc4068c6c5cfe940b"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.workspace_url = config['workspace-url']
        self.scratch = config['scratch']
        # janky, but works for now
        self.sw_url = config.get('kbase-endpoint') + '/service_wizard'
        self.sample_url = config.get('kbase-endpoint') + '/sampleservice'
        self.dfu = DataFileUtil(url=self.callback_url)
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        self.sample_url = config.get('kbase-endpoint') + '/sampleservice'
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
           parameter "ignore_warnings" of Long
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

        sample_set, errors, sample_data_json = import_samples_from_file(
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
        sample_set_ref = None
        html_link = None

        if errors:
            # create UI to display the errors clearly
            html_link = _error_ui(errors, sample_data_json, self.scratch)
        else:
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
                'description': 'Sample Set Import Error ui'
            }]
            report_data['direct_html_link_index'] = 0
        report_info = report_client.create_extended_report(report_data)
        output = {
            'report_ref': report_info['ref'],
            'report_name': report_info['name'],
            'sample_set': sample_set,
            'sample_set_ref': sample_set_ref,
            'errors': errors
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
           parameter "share_within_workspace" of Long
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
            'admin': []
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

    def link_reads(self, ctx, params):
        """
        :param params: instance of type "LinkReadsParams" -> structure:
           parameter "workspace_name" of String, parameter "workspace_id" of
           String, parameter "sample_set_ref" of String, parameter "links" of
           list of type "ReadsLink" (Create links between samples and reads
           objects.) -> structure: parameter "sample_name" of String,
           parameter "reads_ref" of String
        :returns: instance of type "LinkReadsOutput" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String,
           parameter "links" of list of unspecified object
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN link_reads
        logging.info(params)

        ss = SampleService(self.sample_url)

        sample_set_ref = params['sample_set_ref']
        sample_set_obj = self.dfu.get_objects({'object_refs': [sample_set_ref]})['data'][0]['data']
        sample_name_2_info = {d['name']: d for d in sample_set_obj['samples']}

        links = [(d['sample_name'][0], d['reads_ref']) for d in params['links']]

        new_data_links = []
        for sample_name, reads_ref in links:
            sample_id = sample_name_2_info[sample_name]['id']
            version = sample_name_2_info[sample_name]['version']
            sample = ss.get_sample({
                'id': sample_id,
                'version': version,
            })
            ret = ss.create_data_link(
                dict(
                    upa=reads_ref,
                    id=sample_id,
                    version=version,
                    node=sample['node_tree'][0]['id'],
                    update=1,
                )
            )
            new_data_links.append(ret)

        report_client = KBaseReport(self.callback_url)
        report_info = report_client.create_extended_report({
            'workspace_name': params['workspace_name'],
        })
        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref'],
            'links': new_data_links,
        }
        #END link_reads

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method link_reads return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
