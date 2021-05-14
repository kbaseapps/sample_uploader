"""
Mappings for accepted file formats

FILE-FORMAT_verification_mapping: 
FILE-FORMAT_cols_mapping: 
FILE-FORMAT_groups: list of 
"""
import os
import yaml
import urllib
import requests
from .verifiers import *

# with open("/kb/module/lib/sample_uploader/utils/samples_spec.yml") as f:
#     data = yaml.load(f, Loader=yaml.FullLoader)

def _fetch_global_config(config_url, github_release_url, gh_token, file_name):
    """
    Fetch the index_runner_spec configuration file from the Github release
    using either the direct URL to the file or by querying the repo's release
    info using the GITHUB API.
    """
    if config_url:
        print('Fetching config from the direct url')
        # Fetch the config directly from config_url
        with urllib.request.urlopen(config_url) as res:  # nosec
            return yaml.safe_load(res)  # type: ignore
    else:
        print('Fetching config from the release info')
        # Fetch the config url from the release info
        if gh_token:
            headers = {'Authorization': f'token {gh_token}'}
        else:
            headers = {}
        release_info = requests.get(github_release_url, headers=headers).json()
        for asset in release_info['assets']:
            if asset['name'] == file_name:
                download_url = asset['browser_download_url']
                with urllib.request.urlopen(download_url) as res:  # nosec
                    return yaml.safe_load(res)
        raise RuntimeError("Unable to load the config.yaml file from index_runner_spec")

uploader_config = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        "https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/0.4"
    ),
    None,
    "sample_uploader_mappings.yml"
)

SAMP_SERV_CONFIG = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        "https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/0.4"
    ),
    None,
    "metadata_validation.yml"
)

SAMP_ONTO_CONFIG = {k.lower(): v for k, v in _fetch_global_config(
    None,
    os.environ.get(
        'SAMPLE_ONTOLOGY_CONFIG_URL',
        "https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/0.4"
    ),
    None,
    "ontology_validators.yml"
).items()}

default_aliases = {
    'name': [
        "sample name",
        "sample id",
        "samplename",
        "sampleid"
    ],
    'latitude': [
        "lat",
        "geographical latitude",
        "geographical lat",
        "geo lat",
        "geo latitude"
    ],
    'longitude': [
        "long",
        "lon",
        "geographical lon",
        "geographical long",
        "geographical longitude",
        "geo lon",
        "geo long",
        "geo longitude"
    ]
}

shared_fields = uploader_config["shared_fields"]
SESAR_mappings = uploader_config["SESAR"]
ENIGMA_mappings = uploader_config["ENIGMA"]
aliases = uploader_config.get('aliases', default_aliases)
