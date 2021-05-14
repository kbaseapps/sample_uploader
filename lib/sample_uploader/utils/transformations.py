from installed_clients.OntologyAPIClient import OntologyAPI
from sample_uploader.utils.samples_content_error import SampleContentError
from sample_uploader.utils.mappings import SAMP_ONTO_CONFIG
import time
import pandas as pd


_ID_MAP = {
    "envo_ontology": "ENVO:"
}

def _get_timestamp():
    return int(time.time() * 1000)


class FieldTransformer:
    def __init__(self, callback_url):
        self.onto_api = OntologyAPI(callback_url)

    def _ontology_field_transforms(self, row, cols):
        '''
        Transformations related to fields that are validated against an ontology.
        params:
            row - pd.Series, 1 row of a pd.DataFrame.
            cols - all metadata columns of the input DataFrame/Row
        '''
        # find which ontology_cols are in the row.
        onto_cols = set(cols).intersection(set([k.lower() for k in SAMP_ONTO_CONFIG.keys()]))
        for key in onto_cols:
            # first check if already in 'id' form.
            if not row.get(key) or pd.isnull(row[key]):
                continue
            onto_val = str(row[key])
            values = SAMP_ONTO_CONFIG.get(key)[0]
            query_ontology = values.get('ontology')
            id_prefix = _ID_MAP.get(query_ontology)
            if onto_val.startswith(id_prefix):
                continue
            # lower-case and remove white space.
            onto_val = onto_val.lower().strip()
            # check if in appropriate ontology.
            params = {
                'name': onto_val,
                # 'ancestor_term': ,
                'ts': _get_timestamp(),
                'ns': query_ontology
            }
            ret = self.onto_api.get_term_by_name(params)
            # ensure there is only 1 result
            if len(ret['results']) != 1:
                raise SampleContentError(f"Couldn't resolve ontology term. Received {len(ret['results'])} "
                                         f"results from query with params {params} in OntologyAPI, "
                                         f"Expected 1 result.", key=key)
            item = ret['results'][0]
            # assert the name is the same as query name
            ret_name = str(item.get('name', '')).lower().strip()
            if ret_name != onto_val:
                raise SampleContentError(f'name="{ret_name}" in Ontology {query_ontology} '
                                         f'does not match provided {onto_val}', key=key)
            # get the term id.
            id_ = item.get('id')
            # make sure 'id' is in correct format.
            if not id_.startswith(id_prefix):
                raise RuntimeError(f"{id_} not a well-formed 'id' for ontology "
                                   f"{query_ontology}. must start with {id_prefix}")
            # now we set the 'id' as the row.
            row[key] = id_
        return row

    def field_transformations(self, row, cols):
        '''
        central function for performing any tranformations for fields
        in the input DataFrame Row.
        params:
            row - pd.Series, 1 row of a pd.DataFrame.
            cols - all metadata columns of the input DataFrame/Row
        '''
        row = self._ontology_field_transforms(row, cols)
        return row
