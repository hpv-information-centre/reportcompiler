Plugin development
==================

For extensive customizability, all the different stages of the document generation are implemented as plugins with a common interface. Usually, new plugins will only require the implementation of one or more methods.

Besides this implementation, the plugins must be registered. This library uses python `entry points`_ to discover new plugins: basically, each plugin (or group of plugins) should be packaged using setuptools_ and call the *setup* function with the appropriate *entry_points* arguments.

Entry points are defined by three values: **group**, **name** and **object reference**.

The **groups** currently defined represent each one of the different pipeline stages:

* reportcompiler.data_fetchers
* reportcompiler.source_parsers
* reportcompiler.template_renderers
* reportcompiler.postprocessors

Each group can have several entry points defined as a list. The entry point **name** chosen for the plugin will be the one later referenced on each stage declaration ('type' parameter in :ref:`plugin_modules`).

Finally, the **object reference** should be the module path and the class within the module implementing the interface, both parts separated by a colon.

For example, the `HPV Information Centre MySQL plugin`_ has the following parameter in the setup() function:

.. code-block:: python

    entry_points={
        'reportcompiler.data_fetchers': [
            'mysql_ic=reportcompiler_ic_fetcher.mysql_ic:MySQLICFetcher',
        ],
    }

, and, when used as a data fetcher in a fragment, has the following declaration:

.. code-block:: python

    data_fetcher = [
            {
                'name': 'nw',
                'credentials': 'information_center',
                'type': 'mysql_ic',
                'missing_string': '-',
                'table': 'data_m2_cervical_incidence_ci5c',
                'fields': odict[
                    'r.area_name': 'country_name',
                    'M2ICI1009': 'NUM',
                    'M2ICI1006': 'CRUDE',
                    'M2ICI1011': 'ASR',
                ],
                'condition': {
                    'M2ICI1000': 'iso'
                }
            }
    ]


.. _`entry points`: https://packaging.python.org/specifications/entry-points/
.. _setuptools: http://setuptools.readthedocs.io/en/latest/
.. _`HPV Information Centre MySQL plugin`: https://github.com/hpv-information-centre/reportcompiler-ic-fetcher