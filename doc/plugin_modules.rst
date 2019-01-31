.. _`plugin_modules`: 

Plugin modules
==============

The different stages of the document generation pipeline are developed as plugin modules, allowing an easy extendibility for most use cases. 

Plugin specifications are JSON-like structures that define which plugins are used for a particular pipeline stage and how they will work. Document-level specifications are defined in the *config.conf* file while fragment-level specifications are defined in the fragment source file and parsed by the metadata retriever stage. Examples are shown below.

The plugins can be divided in two groups: per-fragment plugins (source parser, data_fetcher) and per-document plugins (template renderer, postprocessor). The resolution method to determine which plugin to use in a particular case uses the following priority:

1. Fragment source file (if it's a per-fragment plugin).
2. Document specification (*config.conf*).
3. Default value (if available).

This allows to set up default plugins for general use and override them when necessary. For instance, we could configure a MySQL data fetcher in the *config.conf* to be used in all fragments but define an Excel fetcher in one particular fragment.

Plugin specifications are selected using a mandatory **type** parameter. This value identifies the type of plugin to be used (see below). In case of specifications as strings, such string will always be the implicit type.

.. _`data_fetchers`: 

Data fetchers
-------------
These modules usually return a pandas_ dataframe with information retrieved from a particular data source, though they could return additional information as well (see reportcompiler-ic-fetcher_).

Each fragment can have several data fetchers assigned, defined by the *data_fetchers* variable in the source file (parsed by the Source Parser plugins). This JSON serializable structure is either a dictionary with the fetcher parameters or a list of fetcher dictionaries.

Each data fetcher implementation receives three arguments: the document parameter, a dictionary with the information related to that fetcher definition and the whole fragment metadata. Note that the whole metadata includes the fetcher definition, but it is necessary to specify separately since a fragment can have more than one data fetcher.

Data fetchers specifications can include a **name** parameter. This parameter is used to index the different fetched dataframes when using the *data* parameter in the context generation stage. If no name is assigned, the dataframe will be indexed as the index of the fetcher in the fetcher list represented as a string (e.g. '0' if there is only one).

The data fetchers currently included in the core library are:

.. _pandas: https://pandas.pydata.org/
.. _reportcompiler-ic-fetcher: https://github.com/hpv-information-centre/reportcompiler-ic-fetcher

.. inheritance-diagram:: 
    reportcompiler.plugins.data_fetchers.constant 
    reportcompiler.plugins.data_fetchers.excel
    reportcompiler.plugins.data_fetchers.mysql
    reportcompiler.plugins.data_fetchers.sqlite
   :parts: 1

Constant
********
**Type name**: 'constant'

This fetcher returns a constant dataframe with a single column named 'value' with the predefined values. This is useful for a (short) list of static values, e.g. continents, or for testing purposes. For a more maintainable use it might be preferable to store this list in a database and use a different data fetcher (mysql, for instance).

Parameters:

* **values**: List of predefined values returned by the fetcher (mandatory).

Example:

.. code-block:: javascript

  "data_fetchers": {
    "name": "continent",
    "type": "constant",
    "values": ["Africa", "America", "Asia", "Europe", "Oceania"]
  }

Excel files
************
**Type name**: 'excel'

This fetcher returns a single worksheet from a MS excel file using the pandas *read_excel* method. The file should be included in the 'data' folder within the document specification.

Parameters:

* **file**: Name of the excel file (mandatory).
* **sheet**: Name (if string) or index (if numeric) of the sheet. By default is 0 (first sheet).
* **columns**: Analogous to the *usecols* argument of the read_excel_ method. That is:
   * If None then parse all columns (default),
   * If int then indicates last column to be parsed
   * If list of ints then indicates list of column numbers to be parsed
   * If string then indicates comma separated list of Excel column letters and column ranges (e.g. “A:E” or “A,C,E:F”). Ranges are inclusive of both sides.
* **na_values**: Analogous to the *na_values* argument of the read_excel_ method. That is:
    Additional strings to recognize as NA/NaN. If dict passed, specific per-column NA values. By default the following values are interpreted as NaN: ‘’, ‘#N/A’, ‘#N/A N/A’, ‘#NA’, ‘-1.#IND’, ‘-1.#QNAN’, ‘-NaN’, ‘-nan’, ‘1.#IND’, ‘1.#QNAN’, ‘N/A’, ‘NA’, ‘NULL’, ‘NaN’, ‘n/a’, ‘nan’, ‘null’.

Example:

.. code-block:: javascript

  "data_fetchers": {
    "name": "continent",
    "type": "excel",
    "file": "continent.xlsx"
  }

.. _read_excel: https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html


MySQL
*******
**Type name**: 'mysql'

This fetcher returns data from a MySQL database as specified by the parameters below.

Parameters:

* **credentials_file**: Name of the JSON file with the credentials to connect to the database, stored in the 'credentials' folder within the document specification. The structure should be a dictionary with the following keys:
  * **host**: Hostname
  * **user**: Username
  * **password**: Password
  * **db**: Database name
   
  It is recommended to avoid this parameter and use **credentials** instead to avoid having passwords in plaintext.
* **credentials**: Name of the credential to be used by the credential manager. It currently needs a JSON file with a dictionary of keys and be setup by the RC_CREDENTIALS_FILE. This alternative is more secure that **credentials_file** but there is no access control in place yet.
* **fields**: Table fields to retrieve (mandatory). It can be a list of fields or a dictionary where each key is the table field and the value is the alias that will be returned.
* **distinct**: Whether to make a a distinct query or not (false by default).
* **table**: Name of the table (mandatory).
* **condition**: Dictionary of conditions (WHERE clause). At this point only equality conditions are considered. Each (key, value) pair corresponds to the table field and the value of the document parameter taken as input. E.g. the pair ('iso3Code', 'iso') is equivalent to the condition *'iso3Code' = doc_var['iso']*. For conditions with constant values see **condition_const**.
* **condition_const**: Similar to **condition**, except the value of each dictionary item corresponds to a literal value. E.g. the pair ('iso3Code', 'ESP') is equivalent to the condition *'iso3Code' = 'ESP'*.
* **join**: Dictionary defining table joins. It can have the following keys:
  * **type**: Type of join, that is, 'left', 'right', 'inner' (default) or 'outer'.
  * **table**: Table to be joined with (mandatory).
  * **on**: Dictionary with (equality) conditions for the join, where each key and value are the terms of the equality (mandatory).
* **group**: List of fields to be grouped by.
* **sort**: List of fields to sort or dictionary with fields as keys and ['ASC', 'DESC'] as keys defining the order. If it is a list ASC order is assumed.
* **limit**: Integer with maximum number of rows to return.
* **offset**: Integer with index of first row that should be returned.
* **raw_query**: String with the SQL query. If specified the rest of SQL query parameters are ignored. to be used only when a very customized query is necessary.

Example:

.. code-block:: javascript

  "data_fetchers": {
    "name": "countries",
    "type": "mysql",
    "credentials": "countries_db",
    "fields": {
      "area_name": "country"
    },
    "table": "areas_tbl",
    "condition": {
      "iso3code": "iso"
    },
    "condition_const": {
      "continent": "Europe"
    }
  }

SQLite
********
**Type name**: 'sqlite'

This fetcher returns data from a SQLite database as specified by the parameters below. The params *fields, distinct, table, condition, condition_const, join, group, sort, limit, offset* and *raw_query* from the MySQL query apply here as well.

Parameters:

* **file**: Filename of the SQLite database. This file should be in the 'data' folder within the document specification.

Example:

.. code-block:: javascript

  "data_fetchers": {
    "name": "countries",
    "type": "sqlite",
    "file": "countries.db",
    "fields": {
      "area_name": "country"
    },
    "table": "areas_tbl",
    "condition": {
      "iso3code": "iso"
    },
    "condition_const": {
      "continent": "Europe"
    }
  }


.. _`source_parsers`: 

Source parsers
--------------

These modules parse the source files for each fragment in order to extract the metadata (including the data fetcher specification) and the context generation code. Thus, each source parser plugin implements two functions: retrieve_metadata and generate_context.

The *retrieve_metadata* function parses the source file and returns a dictionary with the included metadata. This is usually implemented as parsing variable assignments and returning a dictionary with items <variable_name>: <variable_value>. It receives two arguments: the document parameter and the document metadata.

The *generate_context* function generates the fragment context for the template rendering stage. It receives three arguments: the document parameter, the fetched data and the fragment metadata.

By default files get a default parser corresponding to their (case insensitive) file extension, but they can be overridden in the document configuration.

Example ('python' parser for '.py' files and 'r' parser for '.r' files):

.. code-block:: javascript

  "source_parser": {
     ".py": "python",        // 'python' parser for '.py' files
     ".r": "r"               // 'r' parser for '.r' files
  }

The source parsers currently included in the core library are:

.. inheritance-diagram:: 
    reportcompiler.plugins.source_parsers.python
    reportcompiler.plugins.source_parsers.r
   :parts: 1

Python
******

**Type name**: 'python'

Parser for python (3), default parser for .py files.

R
***

**Type name**: 'r'

Parser for R, default parser for .r files.


.. _`template_renderers`: 

Template renderers
------------------

These modules combine the templates in the *templates* directory with the context dictionaries generated in the context generation stage in order to generate a document in the *gen/<doc_suffix>/out* folder. This document will be further refined on the postprocessing stage if necessary.

As an additional tool, an optional common directory referenced by the *RC_TEMPLATE_LIBRARY_PATH* can hold additional templates to be shared among different document specifications. This functionality can be used in further plugins (see `Report Compiler IC Tools`_).

Each template renderer plugin implements three methods: ``render_template``, ``included_templates`` and ``get_fragment_start_comment``.

The ``render_template`` method is responsible for the document generation using templates and data contexts. It has two arguments: the document parameter and the full document context. This context is a dictionary with two items:

* *meta*: the document metadata, with an additional item with key *template_context_info* that contains a list of tuples of (template file, fragment path) for each fragment. The fragment path is the chain of parent fragments separated by dots (e.g. root.parent.child).
* *data*: the context generated in the previous stage, nested by fragment path. 

The ``included_templates`` returns a list of templates included in a particular template file and it is used to determine the template tree structure. It has a single argument: the text content of the template file.

The ``get_fragment_start_comment`` returns a string that will be used as the comment that will be inserted before each fragment template, for debugging purposes. An output language must be defined, otherwise no comment can be defined and the string will be empty (e.g. the base *jinja2* renderer). It has a single argument: the fragment name.

By default the jinja2 template system is used.

.. code-block:: javascript

  "template_renderer": "jinja2"

.. inheritance-diagram:: 
    reportcompiler.plugins.template_renderers.jinja2
    reportcompiler.plugins.template_renderers.rmarkdown
   :parts: 1

.. _Report Compiler IC Tools: https://github.com/hpv-information-centre/reportcompiler-ic-tools-python

Jinja2
*******

**Type name**: 'jinja2'

Template renderer using the jinja2_ template engine.

* Print statements are written ``{{ <var> }}``.
* Blocks are written ``{% <content> %}``.
* Line comments are written ``## <comment>``.
* Block comments are written:

  .. code-block:: latex

    {%
    This block of
    text is a comment
    %}

Template example:

.. code-block:: latex

  ## This is an example of a latex table
  <ul>
    {% for item in list %}
      <li>{{ item.name }}</li>
    {% endfor %}
  </ul>

Since the idea is to compartmentalize the different fragments, an alias for the current fragment context is created with name ``ctx`` (context). For example, the fragment f2 contained in the fragment f1 would have an automatic directive at the start of the f2 template such as ``with ctx = data.f1.f2``. Similarly, the style data in ``meta.style`` is aliased to ``style``.

.. _jinja2: http://jinja.pocoo.org/

Jinja2 (latex)
**************

**Type name**: 'jinja2-latex'

Template renderer using the jinja2_ template engine with a more latex-friendly syntax. The differences with the regular jinja2 renderer are:

* Print statements are written ``\VAR{<var>}``.
* Blocks are written ``\BLOCK{<content>}``.
* Line comments are written ``%# <comment>``.
* Block comments are written:

  .. code-block:: latex

    \COMMENT
    This block of
    text is a comment
    \ENDCOMMENT

* The following filters are available:
   * **escape_tex**: escapes latex characters.
   * **escape_path**: escapes file paths (e.g. spaces or backslashes).
   * **format_date(fmt)**: formats a date string from YYYY-MM-DD to format *fmt* (see strftime documentation).

Template example:

.. code-block:: latex

  %# This is an example of a latex table
  \begin{itemize}
    \BLOCK{for item in list}
      \item{\VAR{item.name}}
    \BLOCK{endfor}
  \end{itemize}

RMarkdown
**********

**Type name**: 'rmarkdown'

Template renderer using the rmarkdown_ syntax. In this case the context generation input is ignored and the templates will be parsed literally, with the document variable and context inserted as variables *doc_var* and *context* respectively.

.. _rmarkdown: https://rmarkdown.rstudio.com/


.. _`postprocessors`: 

Postprocessors
--------------

These modules process the document generated by the template rendering stage for any last touches that might be needed. More than one postprocessing stage can be defined.

Each postprocessor plugin implements a *postprocess* function. This function uses four arguments: the document parameter, the document, a dictionary with the current postprocessor information and the full document context. Like the template rendering stage, this context is a dictionary with two items:

* *meta*: the document metadata, with an additional item with key *template_context_info* that contains a list of tuples of (template file, fragment path) for each fragment. The fragment path is the chain of parent fragments separated by dots (e.g. root.parent.child).
* *data*: the context generated in the previous stage, nested by fragment path. 

Note that the whole context includes the postprocessor definition, but it is necessary to specify separately since a fragment can have more than one postprocessing stage.

.. code-block:: javascript

  "postprocessors": ["pdflatex", ...]

.. inheritance-diagram:: 
    reportcompiler.plugins.postprocessors.pdflatex
    reportcompiler.plugins.postprocessors.pandoc
   :parts: 1

PDFlatex
**********

**Type name**: 'pdflatex'

Postprocessor that compiles a .tex file into a PDF document using pdflatex. A suitable LaTeX environment (e.g. MiKTeX_) should be available in the system with the necessary packages used in the templates.

.. _MiKTeX: https://miktex.org/

Pandoc
*******

**Type name**: 'pandoc'

Postprocessor that uses pandoc_ to convert documents to a large amount of formats. Pandoc should be available in the system.

Currently this plugin is a work in progress and it is not expected to work as expected at this time.

.. _pandoc: https://pandoc.org/