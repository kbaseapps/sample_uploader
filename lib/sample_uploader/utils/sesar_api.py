import requests

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


def retrieve_sample(igsn):
    """
    Retrieve sample profile for given IGSN

    The official SESAR documentation about this endpoint:
    https://www.geosamples.org/interop#Sample-profile-IGSN
    """

    return_format = 'application/json'
    headers = {"accept": return_format}

    url = '{}/{}'.format(_get_igsn_endpoint(), igsn)

    resp = requests.get(url=url, headers=headers)

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

    resp_json = resp.json()

    sample = resp_json.get('sample')

    if not sample:
        raise ValueError(f'Retrieved an empty sample from service\n{resp_json}')

    return sample
