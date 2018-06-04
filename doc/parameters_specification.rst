.. _`parameters_specification`: 

Document parameter specification
================================

In order to have more control over how the parameters are used the following functionalities can be declared in the *params.conf* file (see :ref:`params.conf`):

.. _`parameter_augmentation`: 

Parameter augmentation
**********************

For reusability purposes, document parameters should contain only the necessary information to identify and generate the intended document. Often, though, many fragments within the document require the same associated information dependent on the document parameters. This can, of course,  be solved by getting the dependent data with a data fetcher in each fragment, but to avoid duplicated fetchers parameter augmentation can be used instead.

The parameter augmentation stage is the first stage on the document generation pipeline, before the fragment generation, and it uses a regular data fetcher (see :ref:`data_fetchers`) to retrieve data that will be added to the original document parameter and will be available to the context generation of all fragments. The retrieved dataframe should contain only one row, and each variable in it will be inserted as a new key/value pair in the document parameter dictionary.

For example, if we made a report about countries with data indexed by iso3 codes, we could use a  document parameter with the 'iso' key. In this case we could generate a document about Spain with the following document parameter:

.. code-block:: javascript

  {
    "iso": "ESP"
  }

But we will probably use the name of the country ("Spain") often in the document, so we could use parameter augmentation defined in the params.conf file:

.. code-block:: javascript

   {
	"params_augmentation": {
                    "type": "mysql",
                    "credentials": "information_center",
                    "table": "areas_tbl",
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


.. _`parameter_mandatory`: 

Mandatory parameters
********************

The document parameter can have any number of keys, but some of them might be forced to appear by defining the *params_mandatory* value. This value is a list of the keys that must appear in the document parameter; otherwise, a ValueError will be raised. When generating a list of documents, each document parameter will be checked before the generation process to ensure that all arguments are valid. For instance, a country report might have any number of optional parameters but it might require a country identifier ('iso'):

.. code-block:: javascript

   {
	"params_mandatory": ['iso']
   }


.. _`parameter_allowed_values`: 

Parameter allowed values
************************

It might be of interest to constrain the number of values that a document parameter value can have. Its value should be a data fetcher definition (see :ref:`data_fetchers`), returning a data frame with one column as the document parameter key and one row per possible allowed value. As usual in data fetchers, more than one can be defined if more than one variable needs to be constrained.

For example, if the 'iso' variable should have only values for countries (not continents or other kinds of region), we can constrain it:

.. code-block:: javascript

  "params_allowed_values": [
		{
        "name": "iso",
        "type": "mysql",
        "credentials": "information_center",
        "table": "areas_tbl",
        "fields": ["iso3Code"],
        "condition_const": {
              "type": "Country"
        }
    }
  ]

This information can be accessed before the generation by using the *fetch_allowed_var_values*, for user interface purposes for example. 