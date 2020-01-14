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
    "Relation Type": (controlled_vocab, [["grouped", "co-located"]]),
    # new ones
    "Platform type": (is_string, []),
    "Location description": (is_string, []),
    "Zone": (is_string, []),
    "Latitude (end)": (is_numeric, []),
    "State/Province": (is_string, []),
    "Original archive contact": (is_string, []),
    "Classification": (is_string, []),
    "Vertical Datum": (is_string, []),
    "Original archive": (is_string, []),
    "Platform name": (is_string, []),
    "Collection time (end)": (is_string, []),
    "County": (is_string, []),
    "Size unit": (is_string, []),
    "Depth in Core (min)": (is_numeric, []),
    "Age unit": (is_string, []),
    "Locality": (is_string, []),
    "Age (min)": (is_numeric, []),
    "Sample Description": (is_string, []),
    "Depth in Core (max)": (is_numeric, []),
    "Collection method description": (is_string, []),
    "Elevation end": (is_numeric, []),
    "Other name(s)": (is_string, []),
    "Geological unit": (is_string, []),
    "Collector/Chief Scientist Address": (is_string, []),
    "Easting (m)": (is_numeric, []),
    "Collection time": (is_string, []),
    "Locality description": (is_string, []),
    "Size": (is_string, []),
    "Launch platform name": (is_string, []),
    "Longitude (end)": (is_numeric, []),
    "Depth scale": (is_string, []),
    "Country": (is_string, []),
    "City/Township": (is_string, []),
    "Northing (m)": (is_numeric, []),
    "Sub-object type": (is_string, []),
    "Launch ID": (is_string, []),
    "Age (max)": (is_numeric, []),
    "Geological age": (is_numeric, []),
    "Collection date (end)": (is_date, []),
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
    },{
        "value": "Age (min)",
        "units": "Age unit"
    },{
        "value": "Age (max)",
        "units": "Age unit"
    },{
        "value": "Geological Age",
        "units": "Geological unit"
    },{
        "value": "Collection date (end)",
        "units": "Collection date precision"
    },{
        "value": "Elevation end",
        "units": "Elevation unit"
    },{
        "value": "Depth in Core (max)",
        "units": "Depth scale"
    },{
        "value": "Depth in Core (min)",
        "units": "Depth scale"
    },{
        "value": "Size",
        "units": "Size unit"
    }
]
