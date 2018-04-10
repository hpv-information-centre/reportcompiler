""" credential_manager.py

This module provides access to credentials stored in a secure and convenient
location in a server environment. For this purpose all credentials are stored
in a JSON file whose path is defined in an environment variable
('RC_CREDENTIALS_FILE').

"""

import os
import json

__all__ = ['CredentialManager', ]


# TODO: Finer-grained access control
class CredentialManager:
    """
    Class responsible for retrieving credentials from the credential file
    """
    @staticmethod
    def retrieve(credential_name, manager_type='default', **kwargs):
        manager_dict = {
            'default': CredentialManager._retrieve_credentials
        }
        return manager_dict[manager_type](credential_name, **kwargs)

    @staticmethod
    def _retrieve_credentials(credential_name, **kwargs):
        """
        Returns the information associated with credential_name.
        :param str credential_name: Key of the requested credentials
        :returns: dictionary with the requested credentials.
        :rtype: dict
        """
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
