.. _`getting_started`: 

Getting started
===============

The Report Compiler is a python library that uses document specifications and custom code to compile parameterizable and reusable documents. This specification, along document parameters represented by a dictionary, is processed by a pipeline to generate highly customizable content. The pipeline stages are designed as plugin modules, making it very easy to extend for particular needs.

This library is currently under heavy development so at this time the architecture might change at any time until considered sufficiently mature. It will not be ready for production until significant, real-world usage shows shortcomings/limitations to be considered for potential architecture redesign. Therefore, at this time, the API (particularly the JSON specification) can change between versions.

This library is being developed by the ICO/IARC Information Centre on HPV and Cancer and will be used in our internal report generation tasks.

Summary
-------

To have a quick understanding of the overall architecture and workflow of this library please check :ref:`architecture`.

To check how a document specification is structured see :ref:`document_specification`.

To examine the available options to define document parameters, see :ref:`parameters_specification`.

To see the full list of values the document metadata may include, see :ref:`document_configuration`.

For more information about the different generation stages, its available plugins and how to use them, see :ref:`plugin_modules`.

To learn about the functionalities to debug documents that fail to be generated, see :ref:`debugging`.

To be able to extend this library with the developemtn of customized plugins, see :ref:`plugin_development`.

Finally, to see a glossary of terms used in this library and its documentation, see the :ref:`glossary`.