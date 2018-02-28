Report Compiler
###############

The Report Compiler is a python library that uses JSON specifications and custom code to compile highly parameterizable and reusable reports. This specification,
along a document variable represented by a dictionary, is processed by a pipeline to generate highly customizable documents. The pipeline stages are
designed as plugin modules so the system is very easy to extend for particular needs.

This library is currently under heavy development so at this time the architecture might change at any time until considered sufficiently mature. It will not be ready
for production until significant, real-world usage shows shortcomings/limitations to be considered for potential architecture redesign. Therefore, at this time, the 
JSON specification can change between versions.

This library is being developed by the ICO/IARC Information Centre on HPV and Cancer and will be used in our report generation tasks.

.. image:: HPV_infocentre.png
   :height: 50px
   :align: center
   :target: http://www.hpvcentre.net

Features
============

TODO


Glossary
============

TODO


Architecture
============

TODO: Include pipeline diagram


Sample reports
==============

TODO: Add sample reports for different pipelines


Installation
============

Package
-------

Run 'scripts/install_package.sh'.


Documentation
-------------

Run 'scripts/compile_docs.sh' for HTML documentation. This project uses Sphinx for documentation, so for 
other formats please use 'make' with the appropriate parameters on the doc directory.


Git hooks setup
---------------

Run script on 'scripts/prepare_hooks.sh'.