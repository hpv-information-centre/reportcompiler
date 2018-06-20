.. _`document_styling`: 

Document styling
======================

In order to customize and, at the same time, generalize the looks of the generated documents, additional values can be inserted in the document metadata using the styling settings. These settings defined on *style.conf* are custom values that will be available in the 'style' key within the metadata (that is, ``metadata['style']``), and therefore the document developer has the freedom to define them and use them (in the templates, most often) as they see fit. Examples of styling settings might be colours, sizes, shapes or fonts, among others.

Also, as mentioned in :ref:`style_settings`, the special **data_fetchers** key can be used to add more settings from an external source.

At some point in the future some kind of standardized settings might be implemented.