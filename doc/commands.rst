.. _`commands`: 

Command line tools
======================

To easily access to the functionality of this library some command line tools are available.

Document generation
-------------------

.. code-block:: bash

  report-compile <doc_spec_path> <doc_param1> <doc_param2> ..

Generates a document with the specified document specification and document parameters. Using the :ref:`default_docparam_key` functionality makes it easier to specify these parameters.

Partial document generation
---------------------------

.. code-block:: bash

    report-fragment <doc_spec_path> <fragment_1> .. <fragment_n> -- <doc_param1> <doc_param2> ..

Generates a document with the specified document specification and document parameters, but only with the specified fragments. The parent templates of the specified fragments will also be included for integrity purposes.
