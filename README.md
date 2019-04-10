[![Build Status](https://travis-ci.org/nismod/simim.png?branch=master)](https://travis-ci.org/nismod/simim) [![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT) [![DOI](https://zenodo.org/badge/159637047.svg)](https://zenodo.org/badge/latestdoi/159637047)
# simim - Spatial Interaction Models of Internal Migration

** **work-in-progress** **

# Introduction

This package aims to build a flexible custom population projection generation tool based on spatial interaction models of internal migration within the UK (probably GB only). The tool is intended to be used to model the impact of large and long-term infrastructure changes on population distribution and growth.

The rationale is to take an official population projection (baseline or variant), internal migration data, and additional official figures for factors that may govern migration (employment, housing, GVA etc). The next step is to construct a spatial interaction model of internal migration from this data that meets some (arbitrary) goodness-of-fit criteria. 

Following this, a scenario must be invented that captures some change or changes given by example a future infrastructure project, for example by increasing the housing stock and/or jobs in a specific region. By reapplying the model to the original input data with the scenario applied, a modified migration O-D matrix is generated.

Finally, the change to the O-D matrix can be applied to the original population projection to create a custom variant. The nature of the model means that localised changes have a global impact - so the new variant projection applies to the whole country.

Scenarios can be cumulatively applied over a number of years, e.g. for a 5-year house-building programme. Each subsequent year should use the previous years data *with the scenario applied* as a starting point.

Once a model has been established with a good fit to the data, the model can then be used to examine the (national) impact on migration of significant changes to infrastructure. As in the example illustrated above, changing the attractiveness parameters at a particular location or locations will result in the model producing a modified OD matrix. This data can then be used to create custom population projection variants at a subnational scale. These variant projections can then be integrated into the [ukpopulation](https://github.com/nismod/ukpopulation) package.

Note that although all the base models are constrained to the total number of migrations, applying changes to the emissiveness or attractiveness values will not in general conserve the total. Thus the migrations can be increased or decreased in this methodology. Additionally, attraction- or doubly-constrained models are not suitable here as they do not allow for changes to attractiveness once the model has been calibrated.

The primary case study for this work will be the proposed east-west arc [[1]](#references) (a.k.a. Cambridge-Milton Keynes-Oxford corridor).

## Caveats
- the model can only be as good as the input data - not all input datasets are recent. The latest know dataset that captures intra-LAD migrations (which may become inter- under some scenario) is the 2011 census.  
- the model assumptions are quite simplistic, although inclusion of multiple emission/attraction factors can help.
- the methodology cannot capture changes in fertility, mortality and international migration that a scenario might be expected to affect.

# Example

## Scenario

New housing across the region, new jobs in the three centres (Oxford, Cambridge, Milton Keynes) over the period 2020-2024, result in e.g. about 10000 new household spaces and 50000 jobs in Oxford.

The full scenario dataset is [here](data/scenarios/test.csv).

## Results

![Example fits](doc/img/sim_basic.png)
_Figure 1. Illustrative example of a production-constrained fit to internal migration, population and household count data by LAD.  The axes in the scatterplot are number of migrations (x actual, y model). The line plot is the total population of Oxford (LAD) - baseline projection (black) and scenario-modified projection (red). The map shows where the changed migration reduces the population (blue) and increases it (red). The OD matrix delta here is the difference in the model computed OD matrices with and without a scenario where jobs are created in the centres (Oxford, Milton Keynes, Cambridge) and household spaces are created across the CaMKOx corridor over the period 2020-2024._

![Example population change](doc/img/sim_pops.png)
_Figure 2. Stacked bar charts of the populations of the CaMKOx constituent LADs over the simulation timeline. The graph on the left shows the baseline subnational population projects whilst the graph on the right shows the impact of the scenario described above._


The above models are still under development and more work needs to be done to choose the optimal emitter and attractor categories, use more up-to-date housing data, plus investigate different cost functions (currently a displaced Euclidean distance between LAD centroids). The changes in population from the model is much smaller than would be expected given the scenario applied.

To run this example (see installation instructions below, then):

```bash
(.venv) $ scripts/run.py -c config/gravity.json
```
The example configuration file can be found [here](config/gravity.json).

# Data Requirements
- ONS sub-national population projections
- ONS sub-national housing projections
- Employment and/or related data (e.g. GVA)
- Internal migration data (LAD level)
- Other emissiveness/attractiveness factors as necessary
- **Specific modifications to the some or all of the above that describe a specific infrastructure scenario.**

# Scenarios

## Geography

The scenarios described below apply to all or part of the "CaMKOx" region defined by the following LADs:

| Code    | Name                   |
| ------- | ---------------------- |
|E07000008|Cambridge
|E07000177|Cherwell
|E07000099|North Hertfordshire
|E06000055|Bedford
|E06000056|Central Bedfordshire
|E07000012|South Cambridgeshire
|E06000032|Luton
|E07000179|South Oxfordshire
|E07000004|Aylesbury Vale
|E07000180|Vale of White Horse
|E07000181|West Oxfordshire
|E07000155|South Northamptonshire
|E06000042|Milton Keynes
|E07000178|Oxford
|E06000030|Swindon
|E07000151|Daventry
|E07000154|Northampton
|E07000156|Wellingborough
|E07000009|East Cambridgeshire
|E07000242|East Hertfordshire
|E07000011|Huntingdonshire
|E07000243|Stevenage

In the baseline (principal variant) projection, the population of this region grows from ~3.4M in 2016 to ~4.0M in 2050.

All scenarios are defined as variations to the baseline household and/or population projections. Thus a value of 100 households for a particular area and year represents an increase of 100 new households spaces _over and above_ the projection for that year. 

## Scenario 1: Five new towns

### Definition

Over the period 2020-2050, the net addition of existing household spaces is reduced to 70% of the projection. The deficit, plus an extra 20000 household spaces, is allocated annually to five new towns in the following Local Authority Districts: Aylesbury Vale (2), Central Bedfordshire, South Cambridgeshire, Huntingdonshire.

[dataset](data/scenarios/scenario1.csv)

Population estimate (2050): 5.3M

### Model Results

Housing increase over projection (2050):

Population (2050): 

## Scenario 2: Expansion

### Definition

In this scenario, over the period 2020-2050 some existing settlements are expanded over and above the baseline household projection. All other areas follow the projection. The annual extra ~20000 household spaces are allocated as follows: 

| LAD(s)                           | Allocation |
| -------------------------------- | ---------- |
| Oxford, Milton Keynes, Cambridge | 25%        |
| Bedford                          | 10%        |
| Northamption, Luton, Stevenage   | 5%         |

[dataset](data/scenarios/scenario2.csv)

Population estimate (2050): 5.3M

### Model Results

Population (2050): 

## Scenario 1 and 2 "J" Variant

These variants add jobs as a second attractiveness factor, exactly in line with the placement of household spaces with a ratio of 1 job per household space. 

Whilst an increase in a household space will by definition increase migration to the LAD in which they are build, employment is more complex as people can work in a place that is different to where they live, especially if there are good transport links. A spatial interaction model should not use "jobs in LAD" as an attractor, rather a broader measure of the accessibility of jobs in that LAD (or, ideally, smaller geography)

# Installation

[only tested on ubuntu 18.04LTS]

First non-python deps can be installed thus:
```
$ sudo apt install proj-bin libproj-dev libgeos-3.6.2 libgeos-dev python3-tk
```
(NB travis installs gdal-bin, libgdal-dev, libproj-dev  OS is 16.04)
Then (use of virtualenv* recommended),
```
$ pip install -r requirements.txt
$ ./setup.py install
$ ./setup.py test
```

&ast; conda will be supported at some point (it may already work but hasn't been tested)

# References
[1] National Infrastructure Commission, 2017, [Growth Arc - Completed Study](https://www.nic.org.uk/our-work/growth-arc/)

[2] Oshan, T (2016), [_A primer for working with the Spatial Interaction modeling (SpInt) module in the python spatial analysis library (PySAL)_](http://openjournals.wu.ac.at/region/paper_175/175.html) 
