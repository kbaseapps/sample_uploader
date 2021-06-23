import requests
import pandas as pd
import xmltodict
import datetime
import logging as log
import time
import collections

"""
NCBI REST web service API

This API handles web request to a REST web service provided by NCBI E-utilities

The official NCBI E-utilities documentation about this web service can be found here:
https://www.ncbi.nlm.nih.gov/books/NBK25499

"""

NCBI_BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'


def retrieve_sample_from_ncbi(sample_id, db='biosample', endpoint='efetch.fcgi'):
    """
    Retrieve sample attributes for given sample id using NCBI E-utilities EFetch endpoint

    The official NCBI documentation about this endpoint:
    https://www.ncbi.nlm.nih.gov/books/NBK25499/#_chapter4_EFetch_
    """

    url = '{base}/{endpoint}?db={db}&id={sample_id}&retmode=xml'.format(
                                        base=NCBI_BASE_URL,
                                        endpoint=endpoint,
                                        db=db,
                                        sample_id=sample_id)

    log.info('Start requesting NCBI sample from: {}'.format(url))
    try:
        time.sleep(1)  # in case of server overload, NCBI has 3 query per second limit
        resp = requests.get(url=url)
        resp.raise_for_status()
    except Exception as err:
        raise RuntimeError(f'Error from NCBI service:\n{resp.status_code}:{resp.text}\n{err}')

    try:
        sample_content = xmltodict.parse(resp.content)
    except Exception as err:
        raise RuntimeError(f'Failed to convert response to DICT\n{err}\n{resp.content}')

    sample = _process_sample_content(sample_content)

    return sample


def _process_time_str(time_str):
    """
    Process time string stored in NCBI
    e.g. '2021-02-28T02:29:27.893', '2014-11-06T00:00:00.000'
    """

    if not time_str:
        return None

    date_time_obj = None
    try:
        log.info('Start parsing time_str {}'.format(time_str))
        str_format = '%Y-%m-%dT%H:%M:%S.%f'
        date_time_obj = datetime.datetime.strptime(time_str, str_format)
    except Exception as err:
        log.warning('Cannot parse time\n{}\n{}'.format(time_str, err))

    return date_time_obj


def _is_float(text):

    if text.isalpha():
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def _process_lat_lon_str(lat_lon):
    """
    Process latitude, longitude string stored in NCBI
    e.g. '47.76 N 127.76 W'
    """

    try:
        log.info('Start parsing latitude and longitude from {}'.format(lat_lon))
        latitude, longitude = lat_lon.split(' ')[0], lat_lon.split(' ')[2]

        if not _is_float(latitude):
            log.warning('Parsed latitude string {} is not a digit'.format(latitude))
            latitude = None

        if not _is_float(longitude):
            log.warning('Parsed longitude string {} is not a digit'.format(latitude))
            longitude = None

    except Exception as err:
        log.warning('Cannot parse lat_lon string\n{}\n{}'.format(lat_lon, err))
        latitude = None
        longitude = None

    return latitude, longitude


def _process_sample_content(sample_content):
    """
    Process sample content returned from NCBI EFetch
    """
    sample_dict = dict()

    try:
        bio_sample = sample_content['BioSampleSet']['BioSample']
    except Exception as err:
        raise ValueError('Failed to parse BioSample\n{}\n{}'.format(sample_content, err))

    date_keys = ['publication_date', 'last_update', 'submission_date']
    for key in date_keys:
        date_obj = _process_time_str(bio_sample.get('@{}'.format(key)))
        if date_obj:
            sample_dict[key] = str(date_obj.date())

    sample_dict['name'] = bio_sample['@accession']

    sample_ids = bio_sample.get('Ids', {}).get('Id', [])

    if type(sample_ids) == list:
        for sample_id in sample_ids:
            if type(sample_id) == collections.OrderedDict:
                db_label = sample_id.get('@db_label')
                if db_label == 'Sample name':
                    sample_dict['description'] = sample_id.get('#text')
    elif type(sample_ids) == collections.OrderedDict:
        sample_dict['description'] = sample_ids.get('#text')

    if not sample_dict.get('description'):
        sample_dict['description'] = sample_dict['name']

    owner_info = bio_sample['Owner']

    sample_dict['current_archive'] = owner_info.get('Name')

    owner_contact = owner_info.get('Contacts', {}).get('Contact', {})
    sample_dict['current_archive_contact'] = owner_contact.get('@email')
    owner_name = owner_contact.get('Name', {})
    sample_dict['collector'] = '{} {}'.format(owner_name.get('First'), owner_name.get('Last'))

    attributes = bio_sample.get('Attributes', {}).get('Attribute', [])

    for attribute in attributes:
        attribute_name = attribute.get('@attribute_name')
        if attribute_name == 'lat_lon':
            latitude, longitude = _process_lat_lon_str(attribute.get('#text'))
            if latitude is not None:
                sample_dict['latitude'] = latitude
            if longitude is not None:
                sample_dict['longitude'] = longitude
        else:
            sample_dict[attribute_name] = attribute.get('#text')

    return sample_dict


def ncbi_samples_to_csv(sample_ids, sample_csv):

    if type(sample_ids) != list:
        raise ValueError('Please provide a LIST of NCBI IDs. Provided: {}'.format(type(sample_ids)))

    samples = [retrieve_sample_from_ncbi(sample_id) for sample_id in sample_ids]
    df = pd.DataFrame.from_dict(samples)
    df.set_index('name', inplace=True)

    # print('-'*80)
    # print(df.columns)
    # print('-'*80)

    with open(sample_csv, 'w') as f:
        df.to_csv(f)
