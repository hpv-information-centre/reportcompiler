""" credential_manager.py

This module provides access to credentials stored in a secure and convenient
location in a server environment. For this purpose all credentials are stored
in a JSON file whose path is defined in the RC_CREDENTIALS_FILE environment
variable.

"""

import os
import json

__all__ = ['CredentialManager', ]


# TODO: Finer-grained access control
class CredentialManager:
    """
    Class responsible for retrieving credentials from the credential file. Its
    motivation is to avoid having plaintext credentials in the document
    specification itself, though currently there is no access control to limit
    their use on a user basis.
    """
    @staticmethod
    def retrieve(credential_name, manager_type='default', **kwargs):
        """
        Retrieves generic credentials with the given credential_name. Currently
        there is no access control so it should not be used for sensitive
        applications.

        :param str credential_name: Key of the requested credentials
        :param str manager_type: Type of credential manager, currently only
            'default' available. This should define how (or which) credentials
            are available in future implementations.
        :returns: dictionary with the requested credentials.
        :rtype: dict
        """
        manager_dict = {
            'default': CredentialManager._retrieve_credentials
        }
        return manager_dict[manager_type](credential_name, **kwargs)

    @staticmethod
    def _retrieve_credentials(credential_name, **kwargs):
        if 'RC_CREDENTIALS_FILE' not in os.environ:
            raise EnvironmentError(
                'RC_CREDENTIALS_FILE not set')

        with open(os.environ['RC_CREDENTIALS_FILE'], 'r') as cred_file:
            credentials = cred_file.read()
            try:
                credentials = json.loads(credentials)
                return credentials[credential_name]
            except json.JSONDecodeError:
                raise EnvironmentError(
                    'Credential file is not a valid JSON file')
            except KeyError:
                raise ValueError(
                    'Credential "{}" does not exist'.format(credential_name))
