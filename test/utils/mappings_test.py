
from sample_uploader.utils.mappings import (
    SESAR_aliases,
    SESAR_date_columns,
    SESAR_groups,
)


def test_SESAR_aliases():

    # test 'unit_measurement' transformation rule
    sample_meta_name = 'name'
    expected_aliases = ['sample name', 'Sample Name']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)

    sample_meta_name = 'sesar:depth_in_core_max'
    expected_aliases = ['Depth Max', 'depth in core (max)', 'Depth in Core (max)', 'depth max']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)

    # test 'map' transformation rule
    sample_meta_name = 'sesar:age_max'
    expected_aliases = ['Age (max)', 'age max', 'age (max)', 'Age Max']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)

    sample_meta_name = 'city_township'
    expected_aliases = ['City', 'city', 'city/township', 'City/Township']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)

    # test 'unit_measurement_fixed' transformation rule
    sample_meta_name = 'latitude'
    expected_aliases = ['latitude start',
                        'Latitude Start',
                        'latitude',
                        'Latitude',
                        'latitude (coordinate system: wgs 84)',
                        'Latitude (Coordinate system: WGS 84)']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)

    sample_meta_name = 'longitude'
    expected_aliases = ['longitude start',
                        'Longitude (Coordinate system: WGS 84)',
                        'longitude (coordinate system: wgs 84)',
                        'Longitude Start',
                        'longitude',
                        'Longitude']
    assert set(SESAR_aliases[sample_meta_name]) == set(expected_aliases)


def test_SESAR_date_columns():

    expected_data_cols = ['sesar:collection_date',
                          'sesar:collection_date_end',
                          'sesar:release_date']
    assert set(SESAR_date_columns) == set(expected_data_cols)


def test_SESAR_groups():

    expected_groups = [
                {'units': 'age_unit', 'value': 'sesar:age_max'},
                {'units': 'age_unit_e.g._million_years_ma', 'value': 'sesar:age_max'},
                {'units': 'age_unit', 'value': 'sesar:age_min'},
                {'units': 'age_unit_e.g._million_years_ma', 'value': 'sesar:age_min'},
                {'units': 'sesar:depth_scale', 'value': 'sesar:depth_in_core_max'},
                {'units': 'sesar:depth_scale', 'value': 'sesar:depth_in_core_min'},
                {'units': 'elevation_unit', 'value': 'sesar:elevation_end'},
                {'units': 'elevation_unit', 'value': 'sesar:elevation_start'},
                {'units': 'geological_unit', 'value': 'sesar:geological_age'},
                {'units': 'str:degrees', 'value': 'latitude'},
                {'units': 'str:degrees', 'value': 'latitude_end'},
                {'units': 'str:degrees', 'value': 'longitude'},
                {'units': 'str:degrees', 'value': 'longitude_end'},
                {'units': 'size_unit', 'value': 'sesar:size'}]

    for group in SESAR_groups:
        assert group in expected_groups
