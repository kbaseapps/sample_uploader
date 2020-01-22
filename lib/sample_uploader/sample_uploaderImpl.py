# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os
import json
import uuid

from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.DataFileUtilClient import DataFileUtil
from .utils.importer import import_samples_from_file
from .utils.mappings import SESAR_verification_mapping, SESAR_cols_mapping, SESAR_groups
from .utils.sample_utils import sample_set_to_OTU_sheet
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
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/slebras/sample_uploader"
    GIT_COMMIT_HASH = "1b2cd3c2d44fd7fd8565db2837959b25df32b868"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        # janky, but works for now
        self.sw_url = config.get('kbase-endpoint') + '/service_wizard'
        self.dfu = DataFileUtil(url=self.callback_url)
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        #END_CONSTRUCTOR
        pass


    def import_samples(self, ctx, params):
        """
        :param params: instance of type "ImportSampleInputs" -> structure:
           parameter "sample_file" of String, parameter "workspace_name" of
           String, parameter "workspace_id" of Long, parameter "file_format"
           of String, parameter "description" of String, parameter "set_name"
           of String, parameter "output_format" of String, parameter
           "taxonomy_source" of String, parameter "num_otus" of Long,
           parameter "incl_seq" of Long, parameter "otu_prefix" of String
        :returns: instance of type "ImportSampleOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN import_samples
        desc = params.get('description', None)
        set_name = params.get("set_name")
        if params.get('file_format') == 'SESAR':
            sample_set = import_samples_from_file(
                params,
                self.sw_url,
                ctx['token'],
                SESAR_verification_mapping,
                SESAR_cols_mapping,
                SESAR_groups,
            )
            obj_info = self.dfu.save_objects({
                'id': params.get('workspace_id'),
                'objects': [{
                    "type": "KBaseSets.SampleSet",
                    "data": sample_set,
                    "name": set_name
                }]
            })[0]
            sample_set_ref = '/'.join([str(obj_info[6]), str(obj_info[0]), str(obj_info[4])])
            sample_file_name = os.path.basename(params['sample_file']).split('.')[0] + '_OTU.csv'

            if params.get('output_format') in ['csv', 'xls']:
                otu_path = sample_set_to_OTU_sheet(
                    sample_set,
                    sample_file_name,
                    self.scratch,
                    params
                )
                file_links = [{
                    'path': otu_path,
                    'name': sample_file_name,
                    'label': "OTU template file",
                    'description': "file with each column containing the assigned sample_id and sample "
                                   "name of each saved sample. Intended for uploading OTU data."
                }]
            else:
                file_links = []

            # create report
            report_client = KBaseReport(self.callback_url)
            report_name = "SampleSet_import_report_" + str(uuid.uuid4())
            report_info = report_client.create_extended_report({
                'message': f"SampleSet object named \"{set_name}\" imported.",
                'objects_created': [{'ref': sample_set_ref}],
                'file_links': file_links,
                'report_object_name': report_name,
                'workspace_name': params['workspace_name']
            })
            output = {
                'report_ref': report_info['ref'],
                'report_name': report_info['name'],
                'sample_set': sample_set
            }

        else:
            raise ValueError(f"Only SESAR format is currently supported for importing samples.")
        #END import_samples

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method import_samples return value ' +
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
        sample_set = dfu.get_objects({'objects': [{'ref': sample_set_ref}]})[0]['data'][0]
        otu_path = sample_set_to_OTU_sheet(
            sample_set,
            output_name,
            self.scratch,
            params
        )

        report_client = KBaseReport(self.callback_url)
        report_name = "Generate_OTU_sheet_report_" + str(uuid.uuid4())
        report_info = report_client.create_extended_report({
            'message': f"SampleSet object named \"{set_name}\" imported.",
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
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
