
# To Do's


## Updating samples to new version with app
	what is required:
		- input SampleSet with sample(s) to update
		- input file with some kind of link to sample
			"Link" could be `sample_id` or `sample_name`
		- Some kind of download Samples function (?)
			- this could be a regular app or an option for download
		- Behaviour of update:
			1.) samples in input file totally replace the data in the Sample service
			2.) Samples that don't have an "update" are kept the same.
			3.) sample set is saved as new version of input sample set.
			4.) If the update_existing option is unchecked.
			5.) Samples are first checked against "previous" version to see if there are actually any updates.

