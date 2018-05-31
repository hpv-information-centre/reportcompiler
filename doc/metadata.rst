.. _`metadata`: 


Document and fragment metadata
==============================

When generating the context for a particular fragment, a metadata dictionary is available along with the document parameter and the fetched data. This dictionary is generated following a hierarchical process: the default metadata items for all fragments are the ones defined in the *config.json* and *params.json* files, but each fragment can then add new items or override existing ones in the fragment source file. The method depends on the plugin implementation, but usually a new key/value pair should be implemented as a value assigned to a variable.

Even though new metadata options can be defined as needed (such as the parameters for each plugin, see :ref:`plugin_modules`), here are the ones used by the Report Compiler library:

* doc_name: Simple name of the base document. For actual generated documents a document suffix will be appended to this name.
* verbose_name: Long name of the document.
* main_template: Root template (that includes the rest of templates).
* doc_spec_path: Absolute path to the document specification directory.
* logger_name: Name of the logger, to be used when 
* debug_mode: True if debug mode is enabled, false (default) otherwise. In debug mode a document will be generated in a single thread to facilitate debugging and all errors will be tracked in order to be debugged easily (see `Debugging tools`_).
* skip_unchanged_fragments: True (default) if context generation should be skipped when no changes have been made for a fragment, false otherwise. Changes detected include code (fragment source file), fetched data and metadata. Changes in modules or libraries imported in the source file are not accounted for.
* cache_file: File generated before each fragment context generation that contains the three parameters: document parameter, data and metadata. This allows reproducibility when compiling fragments.
* doc_suffix: Suffix to the filename that identifies the particular document according to a document parameter. The resulting document filename is typically the document name plus this suffix (even though it depends on the corresponding plugin implementation).

* template_renderer: the template renderer plugin to be used (*jinja2* by default).
* source_parser: the source parser(s) to be used. It should be a dictionary with file extensions as keys and source parser module names as values. File extensions are considered case insensitive when resolving the appropriate parser. E.g:

.. code-block:: javascript

  "source_parser": {
    ".py": "python",
    ".r": "r" 
  }

* postprocessor: the postprocessor(s) to be used. It can be a single postprocessor definition or a list of them. A postprocessor can be, similarly to data fetchers, a string with the appropriate name (see :ref:`??`) or, if parameters are needed a dictionary with all the required info (see :ref:`postprocessors`).

* fig_path: Path for figures, pictures and other auxiliary files to create the document.
* hash_path: Path for files with hashes of code, data and metadata. Used to detect if any changes have been made and, if not disabled, skip the generation if there are none.
* log_path: Path for log files.
* tmp_path: Path for temporary files.
* out_path: Path for output results, usually the document.
* data_path: Path for data files, such as static images.
* src_path: Path for source files.
* templates_path: Path for template files.

* fragment_path: Absolute path for current fragment.
* fragment_name: Name of current fragment.

* params_augmentation: Data fetcher specification for parameter augmentation (see :ref:`parameter_augmentation`).
* params_allowed_values: Data fetcher specification for parameter allowed values (see :ref:`parameter_allowed_values`).
* params_mandatory: List of keys that should always appear in the document parameter dictionary.

.. _`Debugging tools`: https://github.com/hpv-information-centre/reportcompiler-debugging-tools