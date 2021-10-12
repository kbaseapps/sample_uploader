# sample_uploader release notes
=========================================
1.0.1
-----
supporting more data type (Assembly, Genome, AMA Genome, etc.) to link_samples appliction

0.0.23 (first released version in prod)
------
* Adding dataid ('samples/[index]') for the create data link call
* Adds support for metadata subkey (ie unit) column errors

0.0.22
------
* cast value type to match validator file

0.0.21
------
* download validator files upon building container
* Improve error UI and add filter-by-select

0.0.20
------
* Adds severity (introduces warnings)

0.0.19
------
* Adds a highlighted table view for sample upload validation errors

0.0.18
------
* Changing necessary field to 'name' from 'id'
* adding aliases mapping

0.0.17
------
* Adding ability to import samples from NCBI web service

0.0.16
------
* Added positional information to sample validation errors
* Improved error text

0.0.15
------
* Adding functionality to import specific IGSN from the SESAR web service

0.0.14
------
* Adding prevalidtion to import_samples
* Adding Github Actions
* Updating Test framework to run quicker.

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
