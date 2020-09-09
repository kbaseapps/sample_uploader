/*
A KBase module: sample_uploader
*/

module sample_uploader {

    typedef string sample_id;

    typedef structure {
        string sample_set_ref;

        string sample_file;
        string workspace_name;
        int workspace_id;
        string file_format;
        string description;
        string set_name;
        int header_row_index;

        string output_format;
        string taxonomy_source;
        int num_otus;
        int incl_seq;
        string otu_prefix;
    } ImportSampleInputs;

    typedef structure {
        sample_id id;
        string name;
    } sample_info;

    typedef structure {
        list<sample_info> samples;
        string description;
    } SampleSet;

    typedef structure {
        string report_name;
        string report_ref;
        SampleSet sample_set;
        string sample_set_ref;
    } ImportSampleOutputs;

    funcdef import_samples(ImportSampleInputs params) returns (ImportSampleOutputs output) authentication required;


    /*
    Generate a customized OTU worksheet using a SampleSet 
    input to generate the appropriate columns.
    */

    typedef structure {
        string workspace_name;
        int workspace_id;
        string sample_set_ref;
        string output_name;
        string output_format;
        int num_otus;
        string taxonomy_source;
        int incl_seq;
        string otu_prefix;
    } GenerateOTUSheetParams;

    typedef structure {
        string report_name;
        string report_ref;
    } GenerateOTUSheetOutputs;

    funcdef generate_OTU_sheet(GenerateOTUSheetParams params) returns (GenerateOTUSheetOutputs output) authentication required;

    typedef structure {
        string sample_set_ref;
        list<string> new_users;
        int is_reader;
        int is_writer;
        int is_admin;
    } update_sample_set_acls_params;

    typedef structure {
        string status;
    } update_sample_set_acls_output;

    funcdef update_sample_set_acls(update_sample_set_acls_params params) returns (update_sample_set_acls_output output) authentication required;

    /*
        export function for samples
    */

    typedef structure {
        string input_ref;
        string file_format;
    } ExportParams;

    typedef structure {
        string shock_id;
    } ExportOutput;

    funcdef export_samples(ExportParams params) returns (ExportOutput output) authentication required;

};
