"""
Mappings for accepted file formats

FILE-FORMAT_verification_mapping: 
FILE-FORMAT_cols_mapping: 
FILE-FORMAT_groups: list of 
"""
from .verifiers import *


# -------
#  SESAR
# -------
# mapping from column to (verification function, additional arguments for function)
SESAR_verification_mapping = {
    "Sample Name": (is_string, []),
    "IGSN": (regex_string, []),
    "Parent IGSN": (regex_string, []),
    "Release Date": (is_date, []),
    "Material": (is_string, []),
    "Field name (informal classification)": (is_string, []),
    "Location Description": (is_string, []),
    "Locality Description": (is_string, []),
    "Collection method": (is_string, []),
    "Purpose": (is_string, []),
    "Latitude": (is_numeric, []),
    "Longitude": (is_numeric, []),
    "Coordinate Precision?": (is_numeric, []),
    "Elevation start": (is_numeric, []),
    "Elevation unit": (is_numeric, []),
    "Navigation type": (is_string, []),
    "Primary physiographic feature": (is_string, []),
    "Name of physiographic feature": (is_string, []),
    "Field program/cruise": (is_string, []),
    "Collector/Chief Scientist": (is_string, []),
    "Collection date": (is_date, []),
    "Collection date precision": (is_string, []),
    "Current archive": (is_string, []),
    "Current archive contact": (is_email, []),
    "Related Identifiers": (is_string, []),
    "Relation Type": (controlled_vocab, [["grouped", "co-located"]]) 
}

SESAR_cols_mapping = {
    "Sample Name": "name",
    "IGSN": "id",
    "Parent IGSN": "parent_id",
}

"""
{
    "value": "",
    "units": "",
    "species": "",
    .....
    "": ""  
}
"""
SESAR_groups = [
    {
        "value": "Elevation start",
        "units": "Elevation unit"
    },{
        "value": "Latitude",
        "units": "str:degrees"
    },{
        "value": "Collection date",
        "units": "Collection date precision"
    },{
        "value": "Longitude",
        "units": "str:degrees"
    }
]
