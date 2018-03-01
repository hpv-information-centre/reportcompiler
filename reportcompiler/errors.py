class FragmentGenerationError(Exception):
    """ Exception that encapsulates the different errors that might occur in
    the compilation of fragments of a document"""
    def __init__(self, message, enclosed_errors_dict):
        Exception.__init__(self, message)
        self.fragment_errors = enclosed_errors_dict

    def __str__(self):
        msg = self.args[0] + '\n'
        for doc, fragments_tb_dict in self.fragment_errors.items():
            for fragment, error in fragments_tb_dict.items():
                if isinstance(error, tuple):
                    error_msg, error_tb = error
                    msg += '[{}] {}:\n {}\n{}'.format(doc,
                                                      fragment,
                                                      ''.join(error_tb[-5:]),
                                                      error_msg)
                else:
                    msg += '[{}] {}:\n {}\n'.format(doc, fragment, error)
        return msg

__all__ = ['FragmentGenerationError', ]