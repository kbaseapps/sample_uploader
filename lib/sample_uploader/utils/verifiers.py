"""
This File contains all the functios used for verifying different datatypes
that occur in an input samples file.

each function should accept a column of pandas.DataFrame and verify that each
value conforms to some convention. All functions should have an option to accept Nan values as input as well.

Functions should error on incorrect input.
"""
import pandas as pd


def is_string(df_col, allow_nan=True):
    if allow_nan:
        return
    if not df_col.isnull().values.any():
        raise ValueError(f"nan value found in column.")


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


def regex_string(df_col, allow_nan=True):
    # TODO
    is_string(df_col)
    pass


def is_date(df_col, allow_nan=True):
    # TODO
    pass


def is_numeric(df_col, allow_nan=True):
    # TODO
    pass


def is_email(df_col, allow_nan=True):
    # TODO
    is_string(df_col)
    pass

verifiers = {
    "is_string": is_string,
    "controlled_vocab": controlled_vocab,
    "regex_string": regex_string,
    "is_date": is_date,
    "is_numeric": is_numeric,
    "is_email": is_email
}

