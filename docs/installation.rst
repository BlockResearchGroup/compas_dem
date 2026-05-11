********************************************************************************
Installation
********************************************************************************

Stable
======

Stable releases are available on PyPI and can be installed with pip.

.. code-block:: bash

    pip install compas_dem


Latest
======

The latest version can be installed from local source.

.. code-block:: bash

    git clone https://github.com/blockresearchgroup/compas_dem.git
    cd compas_dem
    pip install -e .


Development
===========

To install `compas_dem` for development, install from local source with the "dev" requirements.

.. code-block:: bash

    git clone https://github.com/blockresearchgroup/compas_dem.git
    cd compas_dem
    pip install -e ".[dev]"


.. note::

   ``compas_lmgc90`` and ``compas_cra`` are installed automatically alongside
   ``compas_dem`` via pip. In case of installation issues, please refer to their respective
   repositories:

   - `compas_lmgc90 <https://github.com/BlockResearchGroup/compas_lmgc90>`_
   - `compas_cra <https://github.com/BlockResearchGroup/compas_cra>`_