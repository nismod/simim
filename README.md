[![Build Status](https://travis-ci.org/nismod/simim.png?branch=master)](https://travis-ci.org/nismod/simim) [![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT)
# simim - Spatial Interaction Models of Internal Migration

** **work-in-progress** **

NB this package requires the development version of [`ukpopulation`](https://github.com/nismod/ukpopulation)

### Introduction

This package aims to build a flexible custom population projection generation tool based on spatial interaction models of internal migration within the UK (probably GB only). The tool is intended to be used to model the impact of large and long-term infrastructure changes on population distribution and growth.

The rationale is to take an official population projection (baseline or variant), internal migration data, and additional official figures for factors that may govern migration (employment, housing, GVA etc). The next step is to construct a spatial interaction model of internal migration from this data that meets some (arbitrary) goodness-of-fit criteria. 

Following this, a scenario must be invented that captures some change or changes given by example a future infrastructure project, for example by increasing the housing stock and/or jobs in a specific region. By reapplying the model to the original input data with the scenario applied, a modified migration O-D matrix is generated.

Finally, the change to the O-D matrix can be applied to the original population projection to create a custom variant. The nature of the model means that localised changes have a global impact - so the new variant projection applies to the whole country.

Scenarios can be cumulatively applied over a number of years, e.g. for a 5-year house-building programme. Each subsequent year should use the previous years data *with the scenario applied* as a starting point.

Once a model has been established with a good fit to the data, the model can then be used to examine the (national) impact on migration of significant changes to infrastructure. As in the example illustrated above, changing the attractiveness parameters at a particular location or locations will result in the model producing a modified OD matrix. This data can then be used to create custom population projection variants at a subnational scale. These variant projections can then be integrated into the [ukpopulation](https://github.com/nismod/ukpopulation) package.

Note that although all the base models are constrained to the total number of migrations, applying changes to the emissiveness or attractiveness values will not in general conserve the total. Thus the migrations can be increased or decreased in this methodology. Additionally, attraction- or doubly-constrained models are not suitable here as they do not allow for changes to attractiveness once the model has been calibrated.

The primary case study for this work will be the proposed east-west arc [[1]](#references) (a.k.a. Cambridge-Milton Keynes-Oxford corridor).

### Caveats
- the model can only be as good as the input data - not all input datasets are recent. The latest know dataset that captures intra-LAD migrations (which may become inter- under some scenario) is the 2011 census.  
- the model assumptions are quite simplistic, although inclusion of multiple emission/attraction factors can help.
- the methodology cannot capture changes in fertility, mortality and international migration that a scenario might be expected to affect.

### Example

![Example fits](doc/img/sim_basic.png)
_Figure 1. Illustrative example of a production-constrained fit to internal migration, population and household count data by LAD.  The axes in the scatterplot are number of migrations (x actual, y model). The line plot is the total population of Oxford (LAD) - baseline projection (black) and scenario-modified projection (red). The map shows where the changed migration reduces the population (blue) and increases it (red). The OD matrix delta here is the difference in the model computed OD matrices with and without a scenario where household spaces and jobs are created (unevenly) across the CaMKOx corridor over a 5 year period._

The above models are still under development and more work needs to be done to choose the optimal emitter and attractor categories, use more up-to-date housing data, plus investigate different cost functions (currently a displaced Euclidean distance between LAD centroids). The changes in population from the model is much smaller than would be expected given the scenario applied.

To run this example, clone the project and run (from project root):

```bash
$ ./setup.py install --user
$ scripts/run.py -c config/production2.json
```
Some example configuration files can be found here:
- [config/gravity.json](config/gravity.json)
- [config/production.json](config/production.json)
- [config/production2.json](config/production2.json)
- [config/production3.json](config/production3.json)

And scenarios here:
- [data/scenarios/scenario1.csv](data/scenarios/scenario1.csv)
- [data/scenarios/scenario1.csv](data/scenarios/scenario2.csv)

### Data Requirements
- ONS sub-national population projections
- ONS sub-national housing projections
- Employment and/or related data (e.g. GVA)
- Internal migration data (LAD level)
- Other emissiveness/attractiveness factors as necessary
- **Specific modifications to the some or all of the above that describe a specific infrastructure scenario.**

# References
[1] National Infrastructure Commission, 2017, [Growth Arc – Completed Study](https://www.nic.org.uk/our-work/growth-arc/)

[2] Oshan, T (2016), [_A primer for working with the Spatial Interaction modeling (SpInt) module in the python spatial analysis library (PySAL)_](http://openjournals.wu.ac.at/region/paper_175/175.html) 
