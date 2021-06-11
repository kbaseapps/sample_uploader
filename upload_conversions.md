# How fields are converted into upload format

## Core Fields
Core fields are fields that have an expected core functionality in KBASE. They are the only fields that do not have prefixes, which are delimted with the special `:` character. All other fields are considered format specific.
	core field: `field`
	format field: `prefix:field`


------------

The following is the order in which the header fields are converted in the sample_uploader. There is 

## 1.) Converted to upload format
	Firstly, all header columns are converted to upload format. Upload format is all-lower case, white-space is converted to `_`, and `()/` characters are removed.

	Ex:
		`Name` -> `name`
		`hello world` -> `hello_world`
		`CrAzy CAsE` -> `crazy_case`


## 2.) Name field
	The user supplied `name_field` is converted. The string supplied  is converted to `name`, and is used as the primary identifier of the sample.

	if `params['name_field'] = "test name field"` the following conversion will take place:
		`test name field` -> `name`


## 3.) Aliases
	Next the user supplied fields are checked against the template for the upload format supplied in the `file_format` field.
	The `KBASE` format is an exception, and uses no aliases.
	The templates can be found in the [sample_service_validator_config](https://github.com/kbase/sample_service_validator_config/tree/refactor2/templates) repository. Each file contains a list of `Columns` which have a list of `aliases` which will be converted to the column name.

	Ex:
		`Collection Start Date` -> `Collection date`
			# note: this transformation results in the columns `collection_date` because of conversion to the upload_format.


## 4.) Non-alias prefix tranformations
	After the aliases are accounted for, the uploader looks for fields that may have a corresponding `file_format` specific name. I.E. if `field1` is supplied by the user, for which there is no core field.
	
	The order of preference for adding a prefix to a field is as follows: (ex: `params['file_format'] = 'ENIGMA'`)
		1.) Prefix of uploaded format. ex: `enigma:field1`
		2.) Core field.  ex: `field1`
		3.) Prefix of other format. ex: `sesar:field1`, etc.
