Report Compiler
###############

The Report Compiler is a python library that uses JSON specifications and custom code to compile highly parameterizable and reusable reports. This specification,
along a document variable represented by a dictionary, is processed by a pipeline to generate highly customizable documents. The pipeline stages are
designed as plugin modules so the system is very easy to extend for particular needs.

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

TODO


Installation
============

Package
-------

Run script on scripts/install_package.sh


Documentation
-------------

Run script on scripts/compile_docs.sh for HTML documentation. This project uses Sphinx for documentation, so for 
other formats please use 'make' with the appropriate parameters on the doc directory.
