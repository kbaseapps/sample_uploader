/*
A KBase module: sample_uploader
*/

module sample_uploader {

	typedef string sample_id;

	typedef structure {
		string sample_file;
		string workspace_name;
		int workspace_id;
		string file_format;
		string description;
		string set_name;

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

};
