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
import matplotlib.pyplot as plt
import simim.visuals as visuals
from simim.utils import get_config

def main(params):

  scale = "gb"

  v = visuals.Visual(1, 2)

  data = pd.read_csv(os.path.join(params["output_dir"],
                                  "simim_%s_%s_%s" % (params["model_type"], params["base_projection"], params["scenario"])))

  lads = pd.read_csv("data/scenarios/camkox_lads.csv").set_index("geo_code")

  rdata = data[data.GEOGRAPHY_CODE.isin(lads.index)]

  v.stacked_bar((0, 0), rdata, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE_SNPP",
    title="Baseline Projection", xlabel="Year", ylabel="Population", category_mapping=lads)
  v.panel((0,0)).set_ylim([0,4000000])
  v.stacked_bar((0, 1), rdata, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE",
    title="%s Projection" % params["scenario"], xlabel="Year", ylabel="Population", category_mapping=lads)
  v.panel((0,1)).set_ylim([0,4000000])

  # ldata = data[data.GEOGRAPHY_CODE.str.startswith("E09")]
  # v.stacked_bar((0, 0), ldata, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE_ppp", title="Baseline Projection", xlabel="Year", ylabel="Population")
  # #v.panel((0,0)).set_ylim([0,7000000])
  # v.stacked_bar((0, 1), ldata, "GEOGRAPHY_CODE", "PROJECTED_YEAR_NAME", "PEOPLE", title="Scenario 2 Projection", xlabel="Year", ylabel="Population")
  # #v.panel((0,1)).set_ylim([0,7000000])

  v.show()

if __name__ == "__main__":
  main(get_config())
