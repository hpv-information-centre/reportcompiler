.. _`document_configuration`: 

Metadata settings
================================

When generating the context for a particular fragment, a metadata dictionary is available along with the document parameter and the fetched data. This dictionary is generated following a hierarchical process: the default metadata items for all fragments are the ones defined in the *config.conf* and *params.conf* files, but each fragment can then add new items or override existing ones in the fragment source file. The method depends on the plugin implementation, but usually a new key/value pair should be implemented as a value assigned to a variable.

Even though new metadata options can be defined as needed (such as the parameters for each plugin, see :ref:`plugin_modules`), here are the ones used by the Report Compiler library:

Fixed settings
-----------------

These values are defined by the library and are designed to be used when necessary in the context generation stage. They should not be changed by the user.

* **docspec_path**: Absolute path to the document specification directory.

* **fig_path**: Absolute path for figures, pictures and other auxiliary files to create the document.
* **hash_path**: Absolute path for files with hashes of code, data and metadata. Used to detect if any changes have been made and, if not disabled, skip the generation when there are none.
* **log_path**: Absolute path for log files.
* **tmp_path**: Absolute path for temporary files.
* **out_path**: Absolute path for output results, usually the document.
* **data_path**: Absolute path for data files, such as static images.
* **src_path**: Absolute path for source files.
* **templates_path**: Absolute path for template files.

* **fragment_path**: Absolute path for current fragment (when generating a fragment context).
* **fragment_name**: Name of current fragment (when generating a fragment context).

* **cache_file**: Filename generated before each fragment context generation that contains the three parameters: document parameter, data and metadata. This allows reproducibility when compiling fragments.
* **doc_suffix**: Suffix to the filename that identifies the particular document according to a document parameter. The resulting document filename is typically the document name plus this suffix (even though it depends on the corresponding plugin implementation).

* **logger_name**: Name of the logger (for python logging library), to be used as an identifier for the current fragment (if working in parallel) or the document. 

User-defined parameters
------------------------

These settings can be defined by the user on a document-level (config.conf) or a fragment-level (fragment source file).

* **doc_name** (mandatory): Simple name of the base document. For actual generated documents a document suffix will be appended to this name.
* **verbose_name**: Long name of the document. If not available, *doc_name* will be used.
* **main_template** (mandatory): Root template (that includes the rest of templates).
* **debug**: True if debug mode is enabled, false (default) otherwise. In debug mode a document will be generated in a single thread to facilitate debugging and all errors will be tracked in order to be debugged easily (see `Debugging tools`_).
* **skip_unchanged_fragments**: True (default) if context generation should be skipped when no changes have been made for a fragment, false otherwise. Changes detected include code (fragment source file), fetched data and metadata. Changes in modules or libraries imported in the source file are not accounted for.
* **random_seed**: Seed for randomness. This should be used as the initial value for any pseudorandom generator in order to make the whole generation deterministic and reproducible.
* **data_fetcher** (mandatory): the data fetcher(s) plugin(s) to be used. This value often will be defined for each fragment, but if all the fragments use the same data it can be defined on a document level. For more information see :ref:`data_fetchers`.
* **template_renderer**: the template renderer plugin to be used (*jinja2* by default). For more information see :ref:`template_renderers`.
* **source_parser**: the source parser(s) to be used. It should be a dictionary with file extensions as keys and source parser module names as values. File extensions are considered case insensitive when resolving the appropriate parser. E.g:

  .. code-block:: javascript

    "source_parser": {
      ".py": "python",
      ".r": "r" 
    }

  Most of the time it won't be necessary to explicitly define this value since the defaults will work for the usual file extensions. For more information see :ref:`source_parsers`.

* **postprocessor**: the postprocessing stage(s) to be used. It can be a single postprocessor definition or a list of them. A postprocessor can be, similarly to data fetchers, a string with the appropriate name or, if parameters are needed, a dictionary with all the required info (see :ref:`postprocessors`). By default no postprocessing will be used.
* **params_augmentation**: Data fetcher specification for parameter augmentation (see :ref:`parameter_augmentation`).
* **params_allowed_values**: Data fetcher specification for parameter allowed values (see :ref:`parameter_allowed_values`).
* **params_mandatory**: List of keys that should always appear in the document parameter dictionary (see :ref:`parameter_mandatory`).

.. _`Debugging tools`: https://github.com/hpv-information-centre/reportcompiler-debugging-tools