/*
A KBase module: sample_uploader
*/

module sample_uploader {

	typedef string sample_id;

	typedef structure {
		string sample_file;
		string workspace_name;
		string file_format;
	} ImportSampleInputs;

	typedef structure {
		list<sample_id> sample_ids;
	} SampleSet;

    typedef structure {
        SampleSet sample_set;
        string report_ref;
    } ImportSampleOutputs;

    funcdef import_samples(ImportSampleInputs params) returns (ImportSampleOutputs output) authentication required;
};
