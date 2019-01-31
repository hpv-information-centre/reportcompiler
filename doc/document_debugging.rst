.. _`debugging`: 

Document debugging
==================

Maintainability and reproducibility have been an important focus on this library's development from the start. The philosophy behind these generated documents is to establish a seldom updated document specification that can be updated whenever the data sources content change. Figures, tables or other generated artifacts involving customized code are liable to break when new data is introduced, so a mechanism to rapidly detect and fix bugs is required.

Source files
------------

First of all, a special effort should be made to sanitize fetched data in context generation code. Sanity checks will minimize the chance of undetected mistakes when generating a large amount of documents. If identified errors in the data are made explicit the library will be able to inform the user that something is wrong and will avoid generating invalid documents that might not be checked one by one.

If errors are detected, the library will raise a **DocumentGenerationError** exception with a summary of all errors, grouped first by document parameter and then by fragment. This exception has a **fragment_errors** attribute that is suitably structured to be able to be processed programmatically if necessary (e.g. user interfaces). This attribute is a dictionary of document names, containing a dictionary of fragment names (of that document), which contains the errors themselves.

.. code-block:: javascript

        fragment_errors = {
            "document1": {
                "fragment1": ("Error #1", error1_traceback),
                "fragment2": ("Error #2", error2_traceback)
                // more fragments ...
            }
            // more documents ...
        }

For easier error fixing, each time a fragment context is generated a cache file is created with the three parameters used: document parameter, data and metadata. This allows for reproducibility since any context generation can be exactly recreated in the same environment. To further isolate this generation from external environment dependencies, document developers are advised to write code as deterministically as possible.

If randomness is required, the metadata value **random_seed** should be used as the seed for any non-deterministic systems such as pseudorandom generators to preserve the assumption of determinism in the document generation and thus reproducibility.

When a fragment context generation fails and **debug mode** is enabled, this cache file is appended into a special file called **last_debug_errors** inside the **_meta** directory created in the parent directory of the used document specification. The idea is to establish a common "documents" directory with all the available documents in a host so the *_meta* can be shared. Note that since this file will be regenerated for each document generation job, this feature is only intended to be used in a single-user environment.

This *last_debug_errors* file can be parsed by the `report compiler debugging tools`_ to easily debug the failed fragments in the same conditions it failed. See the debugging tools documentation for more info.

.. _`report compiler debugging tools`: https://github.com/hpv-information-centre/reportcompiler-debugging-tools

Templates
---------

The templates will (depending on the plugin implementation) insert a comment with the name of a fragment before each fragment template. This can be useful when checking template mistakes in, for example, the document .tex file in the *tmp* directory before a *pdflatex* compilation.

Partial document generation
---------------------------

In case only a subset of the available fragments are required, the ``generate`` method includes a ``fragments`` parameter to specify which sections should be generated. The excluded fragments will be commented out of the parent templates. The generated document will be created in the same folder determined by the document parameter, but with a suffix indicating which fragments have been generated.

This functionality can be useful, besides for custom, summarized documents, for fast debugging of particular fragments. In this case, the rest of fragments will not be considered and the generation can be considerably faster (even faster than using the cache system).