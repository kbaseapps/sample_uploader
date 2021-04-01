# sample_uploader

this module supports upload of the sample objects into kbase. It accepts '.csv' and '.xls' files in the SESAR format. For specifics on the format visit the SESAR webpage [here](http://www.geosamples.org).

# Setup and test

Add your KBase developer token to `test_local/test.cfg` and run the following:

```bash
$ make
$ kb-sdk test
```

After making any additional changes to this repo, run `kb-sdk test` again to verify that everything still works.


# Uploader User Documentation

The sample uploader sdk application intends to make the uploading process for .tsv/.csv/.xls/.xlsx files with sample metadata information into the KBase SampleService quick and easy. 


## Input arguments

Required Arguments:

	`sample_file` - input file, must be an '.xls','.xlsx','.tsv', or '.csv' file. Read more about the input file requirements in the `Input File Requirements` section

	`file_format` - `SESAR` or `ENIGMA`. Format the upload file is in. This choice determines which column is used as the main identifier, and to small extent how columns are verified and placed into a controlled metadata field.

	`description` - Description attached to the resulting Sample Set object. Should describe the relationship between the samples that are uploaded together.

	`set_name` - Name of output `KBaseSets.SampleSet` object.

Optional input related arguments

	`sample_set_ref` - Existing `KBaseSets.SampleSet` object to combine with input file.  

	`header_row_index` - default=1 (1 indexed). Index (starting from 1) of the Column Name Headers

	`id_field` - default='IGSN' if file_format="SESAR" and 'sampleid' if file_format="ENIGMA".

Optional Output related arguments:

	`output_format` - Format for output OTU file template (.xlsx or .csv). No output is specified by default

	`taxonomy_source` - Not currently supported.

	`num_otus` - Number of OTU's (Operational Taxonomic Units) expected in output file

	`incl_seq` - Whether to include sequence column in output OTU template file

	`otu_prefix` - String prefix to use on the identifiers for each OTU


## Input File Requirements

The input file should have 1 sample per row after the row that contains the column headers (specified by the `header_row_index` argument). Each sample must have an identifier field in order for the SampleSet to be uploaded successfully. This id field is the `IGSN` in the SESAR format and `sampleid` (no spaces) in the ENIGMA format. 

Certain criteria need to be met for controlled fields which are listed in file [here](https://github.com/kbaseIncubator/sample_service_validator_config/blob/master/metadata_validation.yml). Each of these validated fields require all values in that field to conform to a set of rules. For example, 'latitude' must be a number between -90.00 and 90.00.

There are some fields that have/will have different kinds of validation based on the kind of upload format you select. Currently the only field is the `material` field which will use different ontologies to understand the data.

For more complete information on the SampleService, not related to uploading, take a look at he [SampleService documentation](https://github.com/kbase/sample_service/blob/master/README.md).

# Upload Sample Profiles For Specific IGSNs

The sample uploader SDK interface allows users to upload sample profiles for specific IGSNs from the [SESAR web service](https://www.geosamples.org/interop). 

## IGSN uploader interface workflow:
1. The interface uses an [endpoint](https://www.geosamples.org/interop#Sample-profile-IGSN) provided by the SESAR web service to retrieve metadata of the sample. 
2. Retrieved sample profiles are then converted to a ‘.csv’ file in the SESAR format.
3. Prepared SESAR file is uploaded into the KBase Sample Service using the above-mentioned User Documentation Uploader process. 

## Input arguments
`igsns` - IGSNs of samples separated by a comma, e.g., `'IEAWH0001, GEE0000O4’`. 
	  The interface also accepts a `LIST` of IGSNs, e.g., `['IEAWH0001, GEE0000O4’]`.

Since this interface ultimately calls the User Documentation Uploader process mentioned above, all other arguments are exactly the same as the User Documentation Uploader process. 

# SampleSet specification
SampleSet specification used in this module:
```
typedef string sample_id;

typedef structure {
	sample_id id;
	string name;
} sample_info;

typedef structure {
	list<sample_info> samples;
} SampleSet;

```
