
import inspect
from pytest import raises
import os
import uuid

from sample_uploader.utils.ncbi_api import (
    _process_time_str,
    _process_lat_lon_str,
    retrieve_sample_from_ncbi,
    ncbi_samples_to_csv,
)


def start_test():
    testname = inspect.stack()[1][3]
    print('\n*** starting test: ' + testname + ' **')


def test__process_time_str():

    start_test()

    time_str = '2021-02-28T02:29:27.893'
    date_time_obj = _process_time_str(time_str)

    assert date_time_obj.year == 2021
    assert date_time_obj.month == 2
    assert date_time_obj.day == 28
    assert date_time_obj.hour == 2
    assert date_time_obj.minute == 29
    assert date_time_obj.second == 27
    assert date_time_obj.microsecond == 893000

    bad_time_str = '2021-02-28'
    date_time_obj = _process_time_str(bad_time_str)

    assert date_time_obj is None


def test__process_lat_lon_str():

    start_test()

    lat_lon_str = '47.76 N 127.76 W'
    latitude, longitude = _process_lat_lon_str(lat_lon_str)

    assert latitude == '47.76'
    assert longitude == '127.76'

    bad_lat_lon_str = 'A N B W'
    latitude, longitude = _process_lat_lon_str(bad_lat_lon_str)

    assert latitude is None
    assert longitude is None

    bad_lat_lon_str = 'some content'
    latitude, longitude = _process_lat_lon_str(bad_lat_lon_str)

    assert latitude is None
    assert longitude is None


def test_retrieve_sample_from_ncbi():

    start_test()

    ncbi_sample_id = 'SAMN03166112'
    sample = retrieve_sample_from_ncbi(ncbi_sample_id)

    expected_sample_metadata = ['publication_date', 'last_update', 'submission_date',
                                'name', 'description', 'current_archive', 'current_archive_contact',
                                'collector', 'collection_date', 'depth', 'elev', 'env_biome',
                                'env_feature', 'env_material', 'geo_loc_name', 'latitude',
                                'longitude', 'misc_param']
    assert set(sample.keys()) >= set(expected_sample_metadata)

    expected_sample = {
                    'publication_date': '2014-11-06',
                    'last_update': '2021-02-28',
                    'submission_date': '2014-11-06',
                    'name': ncbi_sample_id,
                    'description': 'Seawater-16',
                    'current_archive': 'University of Hawaii',
                    'current_archive_contact': 'jungbluth.sean@gmail.com',
                    'collector': 'Sean Jungbluth',
                    'collection_date': '2011-07-04',
                    'depth': '2661',
                    'elev': '0',
                    'env_biome': 'seawater',
                    'env_feature': 'seawater',
                    'env_material': 'water',
                    'geo_loc_name': 'Pacific Ocean',
                    'latitude': '47.76',
                    'longitude': '127.76',
                    'misc_param': 'Seawater_16'}
    assert expected_sample == {key: sample[key] for key in expected_sample.keys()}

    bad_ncbi_sample_id = 'AABB'
    with raises(Exception) as context:
        retrieve_sample_from_ncbi(bad_ncbi_sample_id)
    expected_err_msg = 'Error from NCBI service'
    assert type(context.value) == RuntimeError
    assert expected_err_msg in str(context.value.args[0])


def test_ncbi_samples_to_csv():

    start_test()

    test_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    ncbi_ids = ['SAMN03166112', 'SAMN04383980']
    sample_csv = 'ncbi_sample_{}.csv'.format(str(uuid.uuid4()))
    sample_csv = os.path.join(test_dir, 'data', sample_csv)
    ncbi_samples_to_csv(ncbi_ids, sample_csv)

    cmp_sample_csv = os.path.join(test_dir, 'example_data', 'ncbi_sample_example.csv')

    with open(sample_csv, 'r') as f1, open(cmp_sample_csv, 'r') as f2:
        sample_content = f1.readlines()
        cmp_content = f2.readlines()

    assert set(sample_content) == set(cmp_content)
