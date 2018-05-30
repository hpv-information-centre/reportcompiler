Architecture
============

Document specification
----------------------

To define how a document will be generated a document specification has to be created. This specification is a directory with the necessary information to generate documents; it includes templates, source files, configuration files or data files among others (more information on :ref:`report_specification`).

.. image:: _static/report-specification-files.svg
   :align: center

The content of the generated documents can be split up and defined in **fragments**, each having a corresponding template (describing its visualization) and source file (describing its processed data).

.. image:: _static/source-templates.svg
   :align: center

These directory structures fully represent a document generation workflow and they can be easily moved, extended or distributed without any unnecessary dependencies. Furthermore, a file structure is a code-friendly environment, being able to seamlessly debug or use version control like any other software project, for example.

Document generation
-------------------

.. image:: _static/report-generation.svg
   :align: center

Once a document specification is made, a document can be generated: first, a document parameter is provided as a dictionary. This parameter is augmented with additional information if necessary and, along with the report metadata, each fragment's context is generated (see below). These fragments are merged into a full context that is used to render the templates (using one of the available template rendering plugins, see :ref:`template_renderers`) to create the document. Optionally, some postprocessing plugins (see :ref:`postprocessors`) can be applied to the document.

Fragment generation
-------------------

.. image:: _static/fragment-generation.svg
   :align: center

Each fragment follows a three-step process. First, the fragment source file is inspected (see :ref:`source_parsers`) for possible metadata to be added or overriden into the report metadata. Then, this metadata and the document parameter is used to fetch the required data from one of the available sources implemented via plugins (see :ref:`data_fetchers`). Finally, this data along with the document parameter and the metadata is used to generate a dictionary (with the same source parser plugin) that will be returned as the context to fill the corresponding template in the template rendering stage (see above).