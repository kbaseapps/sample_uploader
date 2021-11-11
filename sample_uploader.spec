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
        string name_field;

        string output_format;
        string taxonomy_source;
        int num_otus;
        int incl_seq;
        string otu_prefix;

        int share_within_workspace;
        int prevalidate;
        int incl_input_in_output;
        int ignore_warnings;
        int keep_existing_samples;
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

        list<string> external_ids;
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
    } ImportExternalSampleInputs;

    funcdef import_samples_from_IGSN(ImportExternalSampleInputs params) returns (ImportSampleOutputs output) authentication required;

    funcdef import_samples_from_NCBI(ImportExternalSampleInputs params) returns (ImportSampleOutputs output) authentication required;


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
        Create links between samples and other workspace objects.

        currently support:
            KBaseFile.PairedEndLibrary/SingleEndLibrary,
            KBaseAssembly.PairedEndLibrary/SingleEndLibrary,
            KBaseGenomes.Genome
            KBaseMetagenomes.AnnotatedMetagenomeAssembly

    */

    typedef structure {
        string sample_name;
        string obj_ref;
    } ObjsLink;

    typedef structure {
        string workspace_name;
        string workspace_id;
        string sample_set_ref;
        list<ObjsLink> links;
    } LinkObjsParams;

    /*
    input_staging_file_path: tsv or csv file with sample_name and object_name headers
    */
    typedef structure {
        string workspace_name;
        string workspace_id;
        string sample_set_ref;
        string input_staging_file_path;
    } BatchLinkObjsParams;

    typedef structure {
        string report_name;
        string report_ref;
        list<UnspecifiedObject> links;
    } LinkObjsOutput;

    funcdef link_samples(LinkObjsParams params) returns (LinkObjsOutput output) authentication required;

    funcdef batch_link_samples(BatchLinkObjsParams params) returns (LinkObjsOutput output) authentication required;

    /*
    Filter SampleSets
    */

    typedef structure {
        string column;
        string comparison;
        string value;
        string condition;
    } FilterCondition;

    typedef structure {
        string workspace_name;
        string workspace_id;
        string out_sample_set_name;
        list<string> sample_set_ref;
        list<FilterCondition> filter_conditions;
    } FilterSampleSetsParams;

    typedef structure {
        string report_name;
        string report_ref;
    } FilterSampleSetsOutput;

    funcdef filter_samplesets(FilterSampleSetsParams params) returns (FilterSampleSetsOutput output) authentication required;
};
