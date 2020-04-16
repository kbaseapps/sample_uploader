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

def _fetch_global_config(config_url, github_release_url, gh_token):
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
            if asset['name'] == 'sample_uploader_mappings.yml':
                download_url = asset['browser_download_url']
                with urllib.request.urlopen(download_url) as res:  # nosec
                    return yaml.safe_load(res)
        raise RuntimeError("Unable to load the config.yaml file from index_runner_spec")

data = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        "https://api.github.com/repos/kbaseincubator/sample_service_validator_config/releases/25379962"
    ),
    None
)

shared_fields = data["shared_fields"]
SESAR_mappings = data["SESAR"]
ENIGMA_mappings = data["ENIGMA"]
