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
    GIT_COMMIT_HASH = "180dffe89c909ac3e5cb477bc8eede2d0994d05a"

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
        This example function accepts any number of parameters and returns results in a KBaseReport
        :param params: instance of mapping from String to unspecified object
        :returns: instance of type "ReportResults" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
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
            # For now, lets create an output csv
            sample_ids = [s['id'] for s in sample_set['samples']]
            sample_names = [s['name'] for s in sample_set['samples']]
            sample_file_name = os.path.basename(params['sample_file']).split('.')[0] + '_OTU.csv'
            OTU_csv_output =  os.path.join(self.scratch, sample_file_name)
            with open(OTU_csv_output, 'w') as f:
                f.write('sample id,' + ','.join(sample_ids) + '\n')
                f.write('sample name,' + ','.join(sample_names) + '\n')
            # create report
            report_client = KBaseReport(self.callback_url)
            report_name = "SampleSet_import_report_" + str(uuid.uuid4())
            report_info = report_client.create_extended_report({
                'message': "SampleSet object named \"{set_name}\" imported.",
                'objects_created': [{'ref': sample_set_ref}],
                'file_links': [{'path': OTU_csv_output}],
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
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
