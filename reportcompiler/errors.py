""" errors.py

This module defines the error structure that document generation can return.

"""

__all__ = ['DocumentGenerationError', ]


class DocumentGenerationError(Exception):
    """
    Exception that encapsulates the different errors that might occur in
    the compilation of fragments of a document
    """
    def __init__(self, message, enclosed_errors=None):
        """
        Creates new DocumentGenerationError with a particular message and
        a dictionary of enclosed errors (from the failed fragments).

        :param str message: exception message
        :param dict enclosed_errors: dictionary with failed fragments
            errors for each failed document, e.g:
            {'document1': {
                'fragment1': 'Error #1',
                'fragment2': ('Error #2', <error2_traceback>),
                ...
                }
            ...
            }
        """
        Exception.__init__(self, message)
        self.fragment_errors = enclosed_errors

    def __str__(self):
        msg = self.args[0] + '\n'
        count = 0
        if self.fragment_errors is None:
            return msg
        for doc, fragments_tb_dict in self.fragment_errors.items():
            for fragment, error in fragments_tb_dict.items():
                count += 1
                if isinstance(error, tuple):
                    error_msg, error_tb = error
                    msg += '[{}] {}:\n {}\n{}\n\n'.format(doc,
                                                          fragment,
                                                          ''.join(
                                                              error_tb[-5:]),
                                                          error_msg)
                else:
                    msg += '[{}] {}:\n {}\n\n'.format(doc, fragment, error)
        return msg + '{} error/s'.format(count)
