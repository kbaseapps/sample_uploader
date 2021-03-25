
import inspect
from pytest import raises

from sample_uploader.utils.sesar_api import (
    _get_igsn_endpoint,
    retrieve_sample,
)


def start_test():
    testname = inspect.stack()[1][3]
    print('\n*** starting test: ' + testname + ' **')


def fail_retrieve_sample(igsn, error_msg, error_type, contains=True):

    with raises(Exception) as context:
        retrieve_sample(igsn)

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


def test_retrieve_sample():

    start_test()

    igsn = 'IEAWH0001'
    sample = retrieve_sample(igsn)

    expected_sample_metadata = ['qrcode_img_src', 'user_code', 'igsn', 'name', 'sample_type',
                                'publish_date', 'material', 'collection_method', 'purpose',
                                'latitude', 'longitude', 'elevation_unit', 'navigation_type',
                                'primary_location_type', 'primary_location_name',
                                'location_description', 'locality_description',
                                'cruise_field_prgrm', 'collector', 'collection_start_date',
                                'collection_date_precision', 'current_archive',
                                'current_archive_contact']
    assert set(sample.keys()) == set(expected_sample_metadata)

    assert sample['igsn'] == igsn
    assert sample['name'] == 'PB-Low-5'
    assert sample['sample_type'] == 'Individual Sample'
    assert sample['publish_date'] == '2019-06-18'
    assert sample['material'] == 'Soil'
    assert sample['collection_method'] == 'Coring > Syringe'
    assert sample['purpose'] == 'Microbial Characterization 1'
    assert sample['latitude'] == '33.3375'
    assert sample['longitude'] == '81.71861111'
    assert sample['navigation_type'] == 'GPS'
    assert sample['primary_location_type'] == 'Hollow'
    assert sample['primary_location_name'] == 'Tims Branch watershed'
    assert sample['location_description'] == 'Savannah River Site'
    assert sample['locality_description'] == 'Pine Backwater'
    assert sample['cruise_field_prgrm'] == 'Argonne Wetlands Hydrobiogeochemistry SFA'
    assert sample['collector'] == 'Pamela Weisenhorn'
    assert sample['collection_start_date'] == '2019-06-26'
    assert sample['collection_date_precision'] == 'day'
    assert sample['current_archive'] == 'Argonne National Lab'
    assert sample['current_archive_contact'] == 'pweisenhorn@anl.gov'
