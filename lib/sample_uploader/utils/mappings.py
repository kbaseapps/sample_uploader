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
# each mapping contains: 
#   "verification_mapping"
#   "cols_mapping"
#   "groups"
#   "date_cols"

SESAR_mappings = {
    "verification_mapping": {
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
    },
    "cols_mapping": {
        "Sample Name": "name",
        "IGSN": "id",
        "Parent IGSN": "parent_id"
    },
    "groups": [
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
    ],
    "date_cols": [
        "Release Date",
        "Collection date"
    ]
}

# --------------
#     ENIGMA
#  Adams format
# --------------
# all of them are just verified as strings right now....


ENIGMA_mappings = {
    "verification_mapping": {
        "SampleID": (is_string, []),
        "Experiment Name": (is_string, []),
        "Area Name": (is_string, []),
        "Well Name": (is_string, []),
        "Environmental Package": (is_string, []),
        "Material": (is_string, []),
        "Description": (is_string, []),
        "Filter (micron)": (is_numeric, []),
        "Date": (is_string, []),
        "Collection Time": (is_string, []),
        "Time Zone": (is_string, []),
        "Latitude": (is_numeric, []),
        "Longitude": (is_numeric, []),
        "Depth (cm bgs)": (is_numeric, []),
        "Geological Zone": (is_string, []),
        "Recovery Factor": (is_string, []),
        "Method": (is_string, []),
        "Fraction": (is_string, []),
        "Replicate": (is_string, []),
        "Maturation Time": (is_string, []),
        "Treatment": (is_string, []),
        "Temperature (Celsius)": (is_string, []),
        "Moisture (%)": (is_string, []),
        "Pore Water Extraction (microliters)": (is_string, []),
        "Conductivity (mS/cm)": (is_string, []),
        "Redox Potential  (?)": (is_numeric, []),
        "pH": (is_string, []),
        "AODC (cells/g)": (is_numeric, []),
        "DAPI Cell Count (cells/g)": (is_string, []),
        "DNA Picogreen Total (ng)": (is_string, []),
        "Total Carbon (mg/g dry weight)": (is_string, []),
        "Organic Carbon (mg/g dry weight)": (is_numeric, []),
        "Biomass Carbon (mg/g)": (is_string, []),
        "Total Nitrogen (mg/g dry weight)": (is_string, []),
        "BONCAT Activity (cell/g)": (is_numeric, []),
        "Leucine Activity (ngC/day cell}": (is_string, []),
        "Functional Area": (is_string, []),
        "Type of Well": (is_string, []),
        "Top of Casing Stickup (ft)": (is_numeric, []),
        "Top of Casing Elevation (ft AMSL)": (is_numeric, []),
        "Ground Elevation (ft AMSL)": (is_string, []),
        "Installation Method": (is_string, []),
        "Boring (ft BGS)": (is_string, []),
        "Boring Refusal": (is_string, []),
        "Boring Diameter (in)": (is_string, []),
        "Screen Type": (is_string, []),
        "Screened Interval (ft)": (is_numeric, []),
        "Screen Start Depth (ft BGS)": (is_numeric, []),
        "Screen End Depth (ft BGS)": (is_numeric, []),
        "Screen Top Elevation (ft AMSL)": (is_numeric, []),
        "Screen Bottom Elevation (ft AMSL)": (is_numeric, []),
        "Well Casing Type": (is_string, []),
        "Well Casing OD (in)": (is_string, []),
        "Well Casing ID (in)": (is_string, []),
        "Well Casing Depth (ft BGS)": (is_numeric, []),
        "Drive Casing Type": (is_string, []),
        "Drive Casing ID (in)": (is_string, []),
        "Drive Casing OD (in)": (is_string, []),
        "Drive Casing Start Depth (ft BGS)": (is_string, []),
        "Drive Casing End Depth (ft BGS)": (is_string, []),
        "Packing Type": (is_string, []),
        "Packing Depth Start (ft BGS)": (is_string, []),
        "Packing Depth End (ft BGS)": (is_string, []),
        "TopofWeatheredBedrock (ft BGS)": (is_string, []),
        "TopofFreshBedrock (ft BGS)": (is_string, []),
        "Aquifer": (is_string, []),
        "Fractures/Cavities/WaterBreaks": (is_string, []),
        "Other Name": (is_string, []),
        "Screened": (is_string, []),
        "Open": (is_string, []),
        "Well Status": (is_string, []),
        "Condition": (is_string, []),
        "Origination or Plug/Abandon": (is_string, []),
        "Min Water Level (ft AMSL)": (is_string, []),
        "Average Water Level (ft AMSL)": (is_string, []),
        "Max Water Level (ft AMSL)": (is_string, []),
        "Upper Seal Type": (is_string, []),
        "Upper Seal Start Depth (ft BGS)": (is_string, []),
        "Upper Seal End Depth (ft BGS)": (is_string, []),
        "Lower Seal Type (ft BGS)": (is_string, []),
        "Lower Seal Start Depth (ft BGS)": (is_string, []),
        "Lower Seal End Depth (ft BGS)": (is_string, []),
        "Open Casing Type": (is_string, []),
        "Open Casing OD (in)": (is_string, []),
        "Open Casing ID (in)": (is_string, []),
        "Open Casing Depth (ft BGS)": (is_string, []),
        "Open Hole Diameter (in)": (is_string, []),
        "Open Hole Depth (ft BGS)": (is_string, []),
        "Open Interval Start Depth (ft BGS)": (is_string, []),
        "Open Interval End Depth (ft BGS)": (is_string, []),
        "Open Interval Diameter (in)": (is_string, []),
        "Rock Formation":  (is_string, [])
    },
    "cols_mapping": {
        "SampleID": "id",
        "Well Name": "parent_id"
    },
    "groups": [
    ],
    "date_cols": [
        "Date"
    ],
    "column_unit_regex": [
        "\((.+)\)"
    ]
}

