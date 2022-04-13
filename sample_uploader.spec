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
        int propagate_links;
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
        int is_none;

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
            KBaseGenomes.Genome,
            KBaseMetagenomes.AnnotatedMetagenomeAssembly,
            KBaseMetagenomes.BinnedContigs
            KBaseGenomeAnnotations.Assembly,
            KBaseSearch.GenomeSet,
            KBaseSets.AssemblySet,
            KBaseSets.GenomeSet

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
        string metadata_field; /* full metadata field name (e.g. "enigma:foo") */
        string comparison_operator; /* "==", "!=", "in", "not in", ">", "<", ">=", "<=" */
        string value; /* string, number string for numeric comparisons, comma seperated for (not)in */
        string logical_operator; /* "and", "or" */
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
        SampleSet sample_set;
    } FilterSampleSetsOutput;

    funcdef filter_samplesets(FilterSampleSetsParams params) returns (FilterSampleSetsOutput output) authentication required;

    /*
        Get list of metadata keys/columns from a given list of samplesets. Used to populate filter_sampleset dynamic
        dropdown with valid options from a given list of samples.
    */

    typedef structure {
        list<string> sample_set_refs;
    } GetSamplesetMetaParams;

    funcdef get_sampleset_meta(GetSamplesetMetaParams params) returns (list<string> results) authentication required;

    typedef structure {

        string output_object_name;
        string object_type;
        string description;
    } CreateDataSetFromLinksItem;

    typedef structure {
        list<string> sample_set_refs;
        string collision_resolution; /* how to resolve conflicting linked versions, currently "newest" only supported */
        int ws_id;
        list<CreateDataSetFromLinksItem> set_items;
    } CreateDataSetFromLinksParams;

    typedef tuple<int objid, string name, string type,
    string save_date, int version, string saved_by,
    int ws_id, string workspace, string chsum, int size, mapping<string, string> meta>
    ObjectInfo;

    funcdef create_data_set_from_links(CreateDataSetFromLinksParams params) returns (list<ObjectInfo> results) authentication required;

        string workspace_name;
        string workspace_id;
        list<string> obj_refs;
    } ExpireDataLinkParams;

    typedef structure {
        string report_name;
        string report_ref;
    } ExpireDataLinkOutput;

    /*
        Expire data links for a list of given workspace objects.
    */
    funcdef expire_data_link(ExpireDataLinkParams params) returns (ExpireDataLinkOutput output) authentication required;
};
