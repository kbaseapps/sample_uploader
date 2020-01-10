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
        SampleSet sample_set;
        string ref;
    } ImportSampleOutputs;

    funcdef import_samples(ImportSampleInputs params) returns (ImportSampleOutputs output) authentication required;
};
