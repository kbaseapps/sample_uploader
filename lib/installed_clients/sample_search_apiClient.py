# -*- coding: utf-8 -*-
############################################################
#
# Autogenerated by the KBase type compiler -
# any changes made here will be overwritten
#
############################################################

from __future__ import print_function
# the following is a hack to get the baseclient to import whether we're in a
# package or not. This makes pep8 unhappy hence the annotations.
try:
    # baseclient and this client are in a package
    from .baseclient import BaseClient as _BaseClient  # @UnusedImport
except ImportError:
    # no they aren't
    from baseclient import BaseClient as _BaseClient  # @Reimport


class sample_search_api(object):

    def __init__(
            self, url=None, timeout=30 * 60, user_id=None,
            password=None, token=None, ignore_authrc=False,
            trust_all_ssl_certificates=False,
            auth_svc='https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
            service_ver='dev'):
        if url is None:
            url = 'https://kbase.us/services/service_wizard'
        self._service_ver = service_ver
        self._client = _BaseClient(
            url, timeout=timeout, user_id=user_id, password=password,
            token=token, ignore_authrc=ignore_authrc,
            trust_all_ssl_certificates=trust_all_ssl_certificates,
            auth_svc=auth_svc,
            lookup_url=True)

    def filter_samples(self, params, context=None):
        """
        General sample filtering query
        :param params: instance of type "FilterSamplesParams" -> structure:
           parameter "sample_ids" of list of type "SampleAddress" ->
           structure: parameter "id" of type "sample_id" (A Sample ID. Must
           be globally unique. Always assigned by the Sample service.),
           parameter "version" of Long, parameter "filter_conditions" of list
           of type "filter_condition" (Args: metadata_field - should only be
           a controlled_metadata field, if not will error.
           comparison_operator - suppported values for the operators are
           "==", "!=", "<", ">", ">=", "<=", "in", "not in" metadata_values -
           list of values on which to constrain metadata_field with the input
           operator. logical_operator - accepted values for the operators
           are: "and", "or" potential future args: paren_position - None - no
           operation 1 - 2 - add two open paranthesis -1 - -2 - closed
           paranthesis) -> structure: parameter "metadata_field" of String,
           parameter "comparison_operator" of String, parameter
           "metadata_values" of list of String, parameter "logical_operator"
           of String
        :returns: instance of type "FilterSamplesResults" -> structure:
           parameter "sample_ids" of list of type "SampleAddress" ->
           structure: parameter "id" of type "sample_id" (A Sample ID. Must
           be globally unique. Always assigned by the Sample service.),
           parameter "version" of Long
        """
        return self._client.call_method('sample_search_api.filter_samples',
                                        [params], self._service_ver, context)

    def status(self, context=None):
        return self._client.call_method('sample_search_api.status',
                                        [], self._service_ver, context)
