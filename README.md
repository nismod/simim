[![Build Status](https://travis-ci.org/nismod/simim.png?branch=master)](https://travis-ci.org/nismod/simim) [![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT)
# simim - Spatial Interaction Models of Internal Migration

** **work-in-progress** **

### Example

![Example fits](doc/img/sim_basic.png)
_Figure 1. Example of gravity (unconstrained), attraction-constrained and doubly-constrained fits to 2011 census OD, population and household count data by LAD. The axes are number of migrations (x actual, y model)._

The above models fit poorly because  they use only population (as the emitter) and household count (as the attractor) and the cost function is based on Euclidean distance between LAD centroids. 

This package aims to address these shortcomings by developing a more sophisticated model or models with multiple, configurable factors influencing production and attraction.

Once a model has been established with a good fit to the data, the model can then be used to examine the (national) impact on migration of significant changes to infrastructure. For example, changing the attractiveness parameters at a particular location will result in the model producing a modified OD matrix. This data can then be used to create custom population projection variants at a subnational scale. These variant projections can then be integrated into the [ukpopulation](https://github.com/nismod/ukpopulation) package.

The primary case study for this work will be the proposed east-west arc [[1]](#references) (a.k.a. Cambridge-Milton Keynes-Oxford corridor).

![East-west arc in the context of GB](doc/img/gb.png)
_Figure 2. East-west arc in context of GB. LADs included subject to change._

# References
[1] National Infrastructure Commission, 2017, [Growth Arc – Completed Study](https://www.nic.org.uk/our-work/growth-arc/)

[2] Oshan, T (2016), [_A primer for working with the Spatial Interaction modeling (SpInt) module in the python spatial analysis library (PySAL)_](http://openjournals.wu.ac.at/region/paper_175/175.html) 
