# sample_uploader

this module supports upload of the sample objects into kbase. It accepts '.csv' and '.xls' files in the SESAR format. For specifics on the format visit the SESAR webpage [here](http://www.geosamples.org).

# Setup and test

Add your KBase developer token to `test_local/test.cfg` and run the following:

```bash
$ make
$ kb-sdk test
```

After making any additional changes to this repo, run `kb-sdk test` again to verify that everything still works.

# SampleSet specification
SampleSet specification used in this module:
```
typedef string sample_id;

typedef struct {
	list<sample_id> sample_ids;
} SampleSet;

```
