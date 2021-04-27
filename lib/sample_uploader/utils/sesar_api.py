import requests
import pandas as pd
import csv
import logging
import time

"""
SESAR REST web service API

This API handles web request to a REST web service provided by SESAR (the System for Earth Sample Registration)

The official SESAR documentation about this web service can be found here:
https://www.geosamples.org/interop

"""

__author__ = "Tianhao Gu <tgu@anl.gov>"


def _get_igsn_endpoint():
    """
    Retrieve endpoint for getting sample profile for specific IGSN

    The official SESAR documentation about this endpoint:
    https://www.geosamples.org/interop#Sample-profile-IGSN
    """
    return 'https://app.geosamples.org/sample/igsn'


def retrieve_sample_from_igsn(igsn):
    """
    Retrieve sample profile for given IGSN

    The official SESAR documentation about this endpoint:
    https://www.geosamples.org/interop#Sample-profile-IGSN
    """

    logging.info('Start retrieving sample info for {}'.format(igsn))

    return_format = 'application/json'
    headers = {"accept": return_format}

    url = '{}/{}'.format(_get_igsn_endpoint(), igsn)

    try:
        time.sleep(1)
        resp = requests.get(url=url, headers=headers)
    except Exception as err:
        raise RuntimeError(f'Failed to connect to server\n{err}')

    if not resp.ok:
        error = None
        try:
            # process error returned
            # example return in json: {"sample":{"error":"IEAWH1111 is not registered in SESAR."}}
            resp_json = resp.json()
            error = resp_json.get('sample', {}).get('error')
        except Exception:
            if not error:
                error = resp.text

        raise RuntimeError(f'Error from SESAR service:\n{resp.status_code}:{error}')

    try:
        resp_json = resp.json()
    except Exception as err:
        raise RuntimeError(f'Failed to convert response to JSON\n{err}\n{resp.text}')

    sample = resp_json.get('sample')

    if not sample:
        raise ValueError(f'Retrieved an empty sample from service\n{resp_json}')

    return sample


def igsns_to_csv(igsns, sample_csv):
    """
    Merge retrived samples and write samples info to a CSV for the samples uploader
    """

    if type(igsns) != list:
        raise ValueError('Please provide a LIST of IGSNs. Provided: {}'.format(type(igsns)))

    samples = [retrieve_sample_from_igsn(igsn) for igsn in igsns]
    df = pd.DataFrame.from_dict(samples)
    df.set_index('igsn', inplace=True)

    # write SESAR header
    logging.info('Start writting SESAR header to csv: {}'.format(sample_csv))
    try:
        object_type = ', '.join(df.sample_type.unique())
    except Exception:
        object_type = ''
    try:
        user_code = ', '.join(df.user_code.unique())
    except Exception:
        user_code = ''
    with open(sample_csv, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Object Type:', object_type, 'User Code:', user_code])

    logging.info('Start writting samples info to csv: {}'.format(sample_csv))
    with open(sample_csv, 'a') as f:
        df.to_csv(f)
