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
        string id_field;

        string output_format;
        string taxonomy_source;
        int num_otus;
        int incl_seq;
        string otu_prefix;

        int share_within_workspace;
        int prevalidate;
        int incl_input_in_output;
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

    typedef structure {
        string sample_set_ref;

        list<string> igsns;
        string workspace_name;
        int workspace_id;
        string description;
        string set_name;

        string output_format;
        string taxonomy_source;
        int num_otus;
        int incl_seq;
        string otu_prefix;

        int share_within_workspace;
        int prevalidate;
        int incl_input_in_output;
    } ImportSampleIGSNInputs;

    funcdef import_samples_from_IGSN(ImportSampleIGSNInputs params) returns (ImportSampleOutputs output) authentication required;


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
        string workspace_name;
        int workspace_id;

        string sample_set_ref;
        list<string> new_users;
        int is_reader;
        int is_writer;
        int is_admin;

        int share_within_workspace;
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

    /*
        Create links between samples and reads objects.
    */

    typedef structure {
        string sample_name;
        string reads_ref;
    } ReadsLink;

    typedef structure {
        string workspace_name;
        string workspace_id;
        string sample_set_ref;
        list<ReadsLink> links;
    } LinkReadsParams;

    typedef structure {
        string report_name;
        string report_ref;
        list<UnspecifiedObject> links;
    } LinkReadsOutput;

    funcdef link_reads(LinkReadsParams params) returns (LinkReadsOutput output) authentication required;

};
