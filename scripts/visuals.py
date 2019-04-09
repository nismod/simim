#!/usr/bin/env python3

"""
Current capabilities (microsimulation) don't innately have an ability to capture shocks to the system.
Can only be guided by constraints, typically ONS SNPP principal or variant projections
Projection variants not known to exist for specific infrastructure changes, which can have a national impact
To build this into microsimulation models we need to construct a custom projection variant. How?
Spatial interaction model of (internal) migration.  
LAD level
Propose that migrations are a f(distance, population at origin, housing supply at destination)
Take known migration data (OD matrix) and fit this function to the data
Change the housing supply and evaluate the function -> modified OD matrix
Apply modified OD matrix to existing population projection (principal or variant)
"""
import os
import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx
from simim.utils import get_config
#import simim.data_apis as data_apis 
import simim.visuals as visuals
#from scipy.spatial.distance import squareform, pdist

def main():

  scale = "gb"

  v = visuals.Visual(1, 2)

  #v.line((0, 0), list(range(10)), list(range(10)), "x")

  lads = pd.read_csv("data/scenarios/camkox_lads.csv")["geo_code"]

  data = pd.read_csv("data/output/simim_production_ppp_scenario2.csv")
  data = data[data.GEOGRAPHY_CODE.isin(lads)]

  v.stacked_bar((0, 0), data, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE_ppp")
  v.panel((0,0)).set_ylim([0,7000000])
  v.stacked_bar((0, 1), data, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE")
  v.panel((0,1)).set_ylim([0,7000000])
  v.show()

if __name__ == "__main__":
  main()
