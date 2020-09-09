"""
This File contains all the functios used for verifying different datatypes
that occur in an input samples file.

each function should accept a column of pandas.DataFrame and verify that each
value conforms to some convention. All functions should have an option to accept Nan values as input as well.

Functions should error on incorrect input.
"""
import pandas as pd


def is_string(df_col, params):
    if params.get('max-len'):
        for val in df_col.values:
            if val and len(str(val)) > params['max-len']:
                raise ValueError(f"string {val} in column {df_col.name} exceeds max length {params['max-len']}")


def controlled_vocab(df_col, vocab, allow_nan=True):
    for val in df_col.values:
        if pd.isnull(val):
            if allow_nan:
                continue
            else:
                raise ValueError(f"nan value found in column.")
        val = val.lower()
        if allow_nan:
            if not pd.isnull(val) and val not in vocab:
                raise ValueError(f"value \"{val}\" not in accepted vocabulary - {vocab}")
        else:
            if val not in vocab:
                raise ValueError(f"value \"{val}\" not in accepted vocabulary - {vocab}")


def is_date(df_col, allow_nan=True):
    # TODO
    pass


def is_numeric(df_col, params):
    for val in df_col.values:
        if val is not None:
            try:
                val = float(val)
            except Exception as err:
                raise Exception(f"{err} - {val} in column {df_col.name} is not numeric")
            if params.get('lte'):
                if val > params['lte']:
                    raise Exception(f"{val} in column {df_col.name} must be less than or equal to {params['lte']}")
            if params.get('gte'):
                if val < params['gte']:
                    raise Exception(f"{val} in column {df_col.name} must be greater than or equal to {params['gte']}")


verifiers = {
    "string": is_string,
    "controlled_vocab": controlled_vocab,
    "date": is_date,
    "number": is_numeric
}

