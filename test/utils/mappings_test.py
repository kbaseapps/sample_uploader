from sample_uploader.utils.mappings import SESAR_mappings, ENIGMA_mappings, SESAR_aliases


def test_aliases():

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
