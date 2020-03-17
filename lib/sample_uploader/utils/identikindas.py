'''
types of validators:
    - string
    - date
    - enum/controlled vocab
    - min max int and float
'''


def _int_minmax_builder(params: Dict[str, str]):
    """minimum/maximum validator for integers"""
    
    # by default we use min or max float, if no value is provided
    min_val = params.get('min_val', float('-inf'))
    max_val = params.get('max_val', float('inf'))

    key = d['key']

    def validate_int(value: Dict[str, Union(float, int, bool, str)]) -> Optional[str]:
        if value.get(key) != int(value.get(key)):
            return f"Illegal value for key {key}: {value.get(key)}"
        if type(value.get(key)) != int:
            return f"Illegal value for key {key}: {value.get(key)}"
        if value.get(key) < min_val or value.get(key) > max_val:
            return f"Illegal value for key {key}: {value.get(key)}"
        return None
    return validate_int


def _float_minmax_builder(params: Dict[str, str]):
    """minimum/maximum validator for floats"""
    # by default we use min or max float, if no value is provided
    min_val = params.get('min_val', float('-inf'))
    max_val = params.get('max_val', float('inf'))

    key = d['key']

    def validate_float(value: Dict[str, Union(float, int, bool, str)]) -> Optional[str]:
        if type(value.get(key)) != float:
            return f"Illegal value for key {key}: {value.get(key)}"
        if value.get(key) < min_val or value.get(key) > max_val:
            return f"Illegal value for key {key}: {value.get(key)}"
        return None
    return validate_float

Col_groupings = {
    "Location": {
        "Latitude": float(-90.000, 90.000),
        "Latitude (end)": float(-90.000, 90.000),
        "Longitude": float(-180.000, 180.000),
        "Longitude (end)": float(-180.000, 180.000),
        "Locality": str,
        "Location Description": str,
        "Location description": str,
        "Locality Description": str,
        "Field name (informal classification)": str,
        "Elevation start": float,
        "Elevation end": float,
        "Elevation unit": str,
        "County": str,
        "Coordinate Precision?": float,
        "Primary physiographic feature": str,
        "Name of physiographic feature": str,
        "Easting (m)": float,
        "Northing (m)": float,
        "Locality": str,
        "City/Township": str,
        "Country": str,
        "State/Province": str,
        "Zone": str,
        # not sure
        "Depth in Core (min)": float,
        "Depth in Core (max)": float,
    },
    "Identifiers": {
        "Sample Name": str,
        "IGSN": str,
        "Other name(s)": str,
        "Launch ID": str,
        "Related Identifiers": str,
        "Sample Description": str,
    },
    "Connnected identifiers": {
        "Parent IGSN": str,
        "Related Identifiers": str,
    },
    # bad/not specific name
    "Physical properites": {
        "Size": str,
        "Size unit": str,
        "Material": str,
    },
    "Organization": {
        "Collector/Chief Scientist": str,
        "Collector/Chief Scientist Address": str,
        "Field program/cruise": str,
    },
    "Archival": {
        "Original archive": str,
        "Current archive contact": str,
        "Original archive contact": str,
        "Platform name": str,
        "Current archive": str,
        "Launch platform name": str,
    },
    "Temporal data": {
        "Release Date": datetime.date,
        "Age (min)": float,
        "Age (max)": float,
        "Age unit": str,
        "Geological unit": str,
        "Geological age": float,
        "Collection date (end)": datetime.date,
        "Collection time (end)": float / datetime.date,
        "Collection time": float / datetime.date,
        "Collection date": datetime.date,
        "Collection date precision": str,
    },
    "misc.": {
        "Collection method": str,
        "Purpose": str,
        "Navigation type": str,
        "Relation Type": str  # (controlled_vocab, [["grouped", "co-located"]]),
        "Platform type": str,
        "Classification": str,
        "Vertical Datum": str,
        "Collection method description": str,
        "Depth scale": str,
        "Sub-object type": str,
    }
}