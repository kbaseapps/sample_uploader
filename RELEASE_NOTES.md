# sample_uploader release notes
=========================================

0.0.13
------
* Adding link_samples application to link samples to workspace objects (ex. reads)

0.0.12
------
* Adding handling for Public narratives
* Saving sample in public narrative makes sample publicly readable

0.0.11
------
* Completing spec
* Adding 'id_field' and 'header_row_index' parameters
* Cleaning up error handling for more clear error messages

0.0.10
-----
* Adding 'source_meta' field to samples
* Fixing some importer bugs

0.0.9
-----
* Adding more values to the controlled vocabulary.
* fixing exporter bug

0.0.8
-----
* Fixing version updates for samples
* adding sample set exporter function

0.0.7
-----
* Adding in access to sample service config
* Adding ability to update samples to new versions (given same sample name, or kbase_sample_id)
* Now uses sample service config for "Default" units

0.0.6
-----
* Updating for KBaseSets.SampleSet-2.0: including version in samples
* Adding support for controlled_metadata in saved samples

0.0.5
-----
* adding ability to update sample_set from import_samples

0.0.4
-----
* adding in update_samnple_set_acls function

0.0.3
-----
* adding in option for simple ENIGMA uploader and using input file as an output.

0.0.2
-----
* includes options for csv/xls outputs of OTU data as separate app and as part of importer

0.0.1
-----
* minimum viable version

0.0.0
-----
* Module created by kb-sdk init
