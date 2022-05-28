streetpy
==============================
[//]: # (Badges)
[![GitHub Actions Build Status](https://github.com/chourmo/streetpy/workflows/CI/badge.svg)](https://github.com/chourmo/streetpy/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/chourmo/streetpy/branch/master/graph/badge.svg)](https://codecov.io/gh/chourmo/streetpy/branch/master)


**Streetpy** is a python library to analyse streets dataframes based on a multimodal representation.

### Description

A **streetpy** encapsulates a complex representation of streets in a pandas dataframe with spatial functions (from geopandas) and graph functions (from netpandas (https://https://github.com/chourmo/netpandas)).
The base format has one row for each street segment, with attributes for directional accessibility per mode. For example bike and bike_rev columns are filled with data if a bike can use this street.

Processed modes are walk, bike, transit, rail and drive. Other modes may be added later (such as trucks).
A single mode and directed dataframe can be extracted from this base dataframe. It is used to extract shortest path or isochrones, using pandana library.

**Streetpy** provides fast data extraction from openstreetmap based on the osmdatapy (https://https://github.com/chourmo/osmdatapy) and data simplification functions.

**Streetpy** provides some complex street data functions : dataframe conflation (add attrbutes from another street datasource), multiple source-target shortest paths.

Some attibutes can be evaluated : speed from max possible speed based on a hour speed profile, urban context...

**Documentation** is available at [https://pyrosm.readthedocs.io](https://streetpy.readthedocs.io/en/latest/).

### Copyright

Copyright (c) 2022, chourmo


#### Acknowledgements
 
Project based on the 
[Computational Molecular Science Python Cookiecutter](https://github.com/molssi/cookiecutter-cms) version 1.6.
