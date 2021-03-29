
import inspect
from pytest import raises
from mock import patch
import pandas as pd
import os
import uuid

from sample_uploader.utils.sesar_api import (
    _get_igsn_endpoint,
    retrieve_sample_from_igsn,
    igsns_to_csv,
)


def start_test():
    testname = inspect.stack()[1][3]
    print('\n*** starting test: ' + testname + ' **')


def fail_retrieve_sample(igsn, error_msg, error_type, contains=True):

    with raises(Exception) as context:
        retrieve_sample_from_igsn(igsn)

    assert type(context.value) == error_type

    if contains:
        assert error_msg in str(context.value.args[0])
    else:
        assert error_msg == str(context.value.args[0])


def test__get_igsn_endpoint():

    start_test()

    igsn_endpoint = _get_igsn_endpoint()
    expected_igsn_endpoint = 'https://app.geosamples.org/sample/igsn'

    assert igsn_endpoint == expected_igsn_endpoint


def test_retrieve_sample_fail():

    start_test()

    igsn = 'fake_isgn'
    fail_retrieve_sample(igsn, '400:Invalid IGSN', RuntimeError)

    igsn = 'IEAWH9999'  # TODO: this ISGN might become a valid ISGN in the future
    fail_retrieve_sample(igsn, f'404:{igsn} is not registered in SESAR',
                         RuntimeError)

    with patch("sample_uploader.utils.sesar_api._get_igsn_endpoint",
               return_value='http://fake_url'):
        fail_retrieve_sample('IEAWH0001', 'Failed to connect to server',
                             RuntimeError)

    with patch("sample_uploader.utils.sesar_api._get_igsn_endpoint",
               return_value='http://www.google.com'):
        fail_retrieve_sample('', 'Failed to convert response to JSON',
                             RuntimeError)


def test_retrieve_sample_from_igsn():

    start_test()

    igsn = 'IEAWH0001'
    sample = retrieve_sample_from_igsn(igsn)

    expected_sample_metadata = ['qrcode_img_src', 'user_code', 'igsn', 'name', 'sample_type',
                                'publish_date', 'material', 'collection_method', 'purpose',
                                'latitude', 'longitude', 'elevation_unit', 'navigation_type',
                                'primary_location_type', 'primary_location_name',
                                'location_description', 'locality_description',
                                'cruise_field_prgrm', 'collector', 'collection_start_date',
                                'collection_date_precision', 'current_archive',
                                'current_archive_contact']
    assert set(sample.keys()) >= set(expected_sample_metadata)

    expected_sample = {'igsn': igsn,
                       'user_code': 'IEAWH',
                       'name': 'PB-Low-5',
                       'sample_type': 'Individual Sample',
                       'publish_date': '2019-06-18',
                       'material': 'Soil',
                       'collection_method': 'Coring > Syringe',
                       'purpose': 'Microbial Characterization 1',
                       'latitude': '33.3375',
                       'longitude': '81.71861111',
                       'elevation_unit': [],
                       'navigation_type': 'GPS',
                       'primary_location_type': 'Hollow',
                       'primary_location_name': 'Tims Branch watershed',
                       'location_description': 'Savannah River Site',
                       'locality_description': 'Pine Backwater',
                       'cruise_field_prgrm': 'Argonne Wetlands Hydrobiogeochemistry SFA',
                       'collector': 'Pamela Weisenhorn',
                       'collection_start_date': '2019-06-26',
                       'collection_date_precision': 'day',
                       'current_archive': 'Argonne National Lab',
                       'current_archive_contact': 'pweisenhorn@anl.gov'}
    assert expected_sample == {key: sample[key] for key in expected_sample.keys()}


def test_igsns_to_csv():

    start_test()

    test_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    igsns = ['IEAWH0001', 'GEE0000O4', 'ODP000002']
    sample_csv = 'isgn_sample_{}.csv'.format(str(uuid.uuid4()))
    sample_csv = os.path.join(test_dir, 'data', sample_csv)
    igsns_to_csv(igsns, sample_csv)

    cmp_sample_csv = os.path.join(test_dir, 'example_data', 'isgn_sample_example.csv')

    with open(sample_csv, 'r') as f1, open(cmp_sample_csv, 'r') as f2:
        sample_content = f1.readlines()
        cmp_content = f2.readlines()

    assert set(sample_content) == set(cmp_content)
