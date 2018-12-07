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
from simim.utils import get_shapefile, get_config
import simim.visuals as visuals
#from scipy.spatial.distance import squareform, pdist

def main(params):

  scale = "gb"

  v = visuals.Visual(1,1, panel_y=8 if scale=="gb" else 5)

  # figsize=(9, 9) if scale != "gb" else (6,9)
  # fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize, sharex=False, sharey=False)

  ctrlads = ["E07000178", "E06000042", "E07000008"]
  arclads = ["E07000181", "E07000180", "E07000177", "E07000179", "E07000004", "E06000032", "E06000055", "E06000056", "E07000011", "E07000012"]

  # Local_Authority_Districts_December_2016_Ultra_Generalised_Clipped_Boundaries_in_Great_Britain
  url = "https://opendata.arcgis.com/datasets/686603e943f948acaa13fb5d2b0f1275_4.zip?outSR=%7B%22wkid%22%3A27700%2C%22latestWkid%22%3A27700%7D"
  gdf = get_shapefile(url, params["cache_dir"])

  # england
  if scale == "e":
    xlim = [120000, 670000]
    ylim = [ 00000, 550000]
  # closeup
  elif scale == "closeup":
    xlim =[380000, 600000]
    ylim = [130000, 350000]
  else:
    # fit all the polygons
    xlim=None
    ylim=None

  v.polygons((0), gdf, xlim, ylim)
  v.polygons((0), gdf[gdf.lad16cd.isin(arclads)], xlim, ylim, edge_colour="darkgrey", fill_colour="orange")
  v.polygons((0), gdf[gdf.lad16cd.isin(ctrlads)], xlim, ylim, edge_colour="darkgrey", fill_colour="red")

  v.show()
  v.to_png(os.path.join("doc/img", scale + ".png"))

if __name__ == "__main__":
  main(get_config())
