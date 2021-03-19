This directory should contain scripts and files needed to test your module's code.
 
# Workflows to test
1.  (1) Behavior of Controlled/User metadata
2.  () Export samples
3.  (1) Update a sample/sample version
4.  (1) SESAR format changes
5.  (2) ENIGMA format changes
6.  (2) test '.xls'
7.  (3) test '.csv'
8.  (1) test '.tsv'
9.  (1) test OTU sheet generation (wonder if we still need this)
10. (2) test combine sample sets
11. (1) test the inclusion of `id_field` argument
12. (3) test error states
13. (1) check sample permission match workspace
14. () Change of ACLS application


# Test files to have
1.  filename: fake_samples.tsv
file ext: .tsv, file format: SESAR
	each row in file should test a different thing
	Things to test with this file: 
		Controlled vs User metadata
		Test matching acls to ws
		test `id_field` param

2. filename: fake_samples_ENIGMA.xlsx
	file ext: .xlsx, file format: ENIGMA
	Things tested in this file:

3. filename: error_file.csv
	file ext: .csv, file format: ENIGMA
