.. _`report_specification`: 

Report specification
====================

Each report specification is contained in a directory with the following content.

.. image:: _static/report-specification-files.svg


config.json
-----------

This JSON file contains the report specification parameters (a more detailed list of possible 
values can be found in :ref:`config-parameters`). Before being parsed, this file is minified_, 
allowing for Javascript-style comments (i.e. //, /\*, \*/).

.. _minified: https://en.wikipedia.org/wiki/Minification_(programming)

params.json
-----------

This JSON file extends config.json with other settings related to the report parameters:

.. _`parameter_augmentation`: 

Parameter augmentation
**********************

For reusability purposes, document parameters should contain only the necessary information
to identify and generate the intended document. Often, though, many fragments within the document
require the same associated information dependent on the document parameters. This can, of course, 
be solved by getting the dependent data with a data fetcher in each fragment, but to avoid duplicated fetchers
parameter augmentation can be used instead.

The parameter augmentation stage is the first stage on the document generation pipeline, before
the fragment generation, and it uses a regular data fetcher (see :ref:`data_fetchers`) to retrieve data that will be added
to the original document parameter and will be available to the context generation of all fragments. The
retrieved dataframe should contain only one row, and each variable in it will be inserted as a 
new key/value pair in the document parameter dictionary.

For example, if we made a report about countries with data indexed by iso3 codes, we could use a 
document parameter with the 'iso' key. In this case we could generate a document about Spain with
the following document parameter:

.. code-block:: javascript

  {
    "iso": "ESP"
  }

But we will probably use the name of the country ("Spain") often in the document, so we could use
parameter augmentation defined in the params.json file:

.. code-block:: javascript

   {
	"params_augmentation": {
                    "type": "mysql",
                    "credentials": "information_center",
                    "table": "ref_country_full",
                    "fields": {
                        "area_name": "country_name",
                        "Continent": "continent"
                    },
                    "condition": {
                                "iso3Code": "iso"
                    }
                }
   }

By doing so, the document parameter each fragment would receive would be:

.. code-block:: javascript

   {
    "iso": "ESP",
    "country_name": "Spain",
    "continent": "Europe"
   }

.. _`parameter_allowed_values`: 

Parameter allowed values
************************

TODO


.. _`parameter_mandatory`: 

Mandatory parameters
********************

TODO