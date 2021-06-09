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
from sample_uploader.utils.parsing_utils import upload_key_format
from .verifiers import *

# with open("/kb/module/lib/sample_uploader/utils/samples_spec.yml") as f:
#     data = yaml.load(f, Loader=yaml.FullLoader)

CONFIG_TAG_VERSION = "0.6"


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


def _fetch_gh_token():
    gh_token = os.environ.get('GH_TOKEN')

    if not gh_token:
        # TODO: this is Tian's personal token. Should be removed once environment variable is set up.
        gh_token = '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'

    return gh_token


gh_token = _fetch_gh_token()

uploader_config = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        f"https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/{CONFIG_TAG_VERSION}"
    ),
    gh_token,
    "sample_uploader_mappings.yml"
)

SESAR_config = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        f"https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/{CONFIG_TAG_VERSION}"
    ),
    gh_token,
    "sesar_template.yml"
)

ENIGMA_config = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        f"https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/{CONFIG_TAG_VERSION}"
    ),
    gh_token,
    "enigma_template.yml"
)

SAMP_SERV_CONFIG = _fetch_global_config(
    None,
    os.environ.get(
        'CONFIG_RELEASE_URL',
        f"https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/{CONFIG_TAG_VERSION}"
    ),
    gh_token,
    "metadata_validation.yml"
)

SAMP_ONTO_CONFIG = {k.lower(): v for k, v in _fetch_global_config(
    None,
    os.environ.get(
        'SAMPLE_ONTOLOGY_CONFIG_URL',
        f"https://api.github.com/repos/kbase/sample_service_validator_config/releases/tags/{CONFIG_TAG_VERSION}"
    ),
    gh_token,
    "ontology_validators.yml"
).items()}

CORE_FIELDS = [
    field.lower() for field in SAMP_SERV_CONFIG['validators'] if ":" not in field
]

NON_PREFIX_TO_PREFIX = {}
for field in SAMP_SERV_CONFIG['validators']:
    if ":" in field:
        prefix, field_name = field.lower().split(':')
        if field_name in NON_PREFIX_TO_PREFIX:
            NON_PREFIX_TO_PREFIX[field_name].append(field.lower())
        else:
            NON_PREFIX_TO_PREFIX[field_name] = [field.lower()]


def alias_map(col_config):
    """
    aliases map
    Expand all the aliases into a map
    This maps from the alias name to the proper column name
    """
    aliases = dict()
    for col, rules in col_config.items():
        col_aliases = rules.get('aliases', [])
        col_aliases.append(col)
        col_aliases = list(set(col_aliases))

        transformations = rules.get('transformations')

        if not transformations:
            aliases[col] = col_aliases
        else:
            first_trans = transformations[0]
            parameters = first_trans.get('parameters', [col])
            sample_meta_name = parameters[0]
            aliases[sample_meta_name] = col_aliases

    return aliases


def find_date_col(col_config):
    date_cols = list()

    target_keys = [col for col in col_config.keys()
                   if 'date' in col.lower() and 'precision' not in col.lower()]
    for key in target_keys:
        rules = col_config[key]

        transformations = rules.get('transformations')
        if not transformations:
            date_cols.append(key)
        else:
            first_trans = transformations[0]
            parameters = first_trans.get('parameters', [key])
            sample_meta_name = parameters[0]
            date_cols.append(sample_meta_name)

    return date_cols


def create_groups(col_config):
    groups = list()

    for col, rules in col_config.items():

        transformations = rules.get('transformations')

        if transformations:
            first_trans = transformations[0]
            transform = first_trans.get('transform')

            if transform == 'unit_measurement':
                parameters = first_trans.get('parameters')

                value = parameters[0]
                unit_key = parameters[1]
                unit_rules = col_config[unit_key]
                unit_transformations = unit_rules.get('transformations')

                if not unit_transformations:
                    unit_keys = [unit_key]
                    unit_aliases = unit_rules.get('aliases', [])
                    if unit_aliases:
                        unit_keys += unit_aliases

                    unit_keys = list(set([upload_key_format(unit) for unit in unit_keys]))

                else:
                    first_trans = unit_transformations[0]
                    parameters = first_trans.get('parameters', [col])
                    unit_keys = [upload_key_format(parameters[0])]

                for unit in unit_keys:
                    groups.append({'units': unit, 'value': value})
            elif transform == 'unit_measurement_fixed':
                parameters = first_trans.get('parameters')
                value = parameters[0]
                unit = 'str:{}'.format(parameters[1])

                groups.append({'units': unit, 'value': value})

    return groups


SESAR_aliases = alias_map(SESAR_config['Columns'])
SESAR_date_columns = find_date_col(SESAR_config['Columns'])
SESAR_groups = create_groups(SESAR_config['Columns'])

ENIGMA_aliases = alias_map(ENIGMA_config['Columns'])
ENIGMA_date_columns = find_date_col(ENIGMA_config['Columns'])
ENIGMA_groups = create_groups(ENIGMA_config['Columns'])

SESAR_mappings = dict()
SESAR_mappings['groups'] = SESAR_groups
SESAR_mappings['date_columns'] = SESAR_date_columns

ENIGMA_mappings = dict()
ENIGMA_mappings['groups'] = ENIGMA_groups
ENIGMA_mappings['date_columns'] = ENIGMA_date_columns

aliases = {
    "sesar": SESAR_aliases,
    "enigma": ENIGMA_aliases,
    # "kbase": {**SESAR_aliases, **ENIGMA_aliases}
}
