#

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

import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx

#from scipy.spatial.distance import squareform, pdist

scale = "gb" # "gb" "e" "closeup"


figsize=(9, 9) if scale != "gb" else (5,9)
fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize, sharex=False, sharey=False)

ctrlads = ["E07000178", "E06000042", "E07000008"]
arclads = ["E07000181", "E07000180", "E07000177", "E07000179", "E07000004", "E06000032", "E06000055", "E06000056", "E07000011", "E07000012"]

gdf = geopandas.read_file("../Mistral/data/Local_Authority_Districts_December_2016_Ultra_Generalised_Clipped_Boundaries_in_Great_Britain.shp")

# dists = pd.DataFrame(squareform(pdist(pd.DataFrame({"e": gdf.bng_e, "n": gdf.bng_n}))), columns=gdf.lad16cd.unique(), index=gdf.lad16cd.unique())
# # turn matrix into table
# dists = dists.stack().reset_index().rename({"level_0": "orig", "level_1": "dest", 0: "dist"}, axis=1)
# print(dists.head())

# print(dists.ix[dists.dist.idxmax()])

print(gdf.columns.values)
print(gdf[gdf.lad16cd.isin(arclads)][["lad16nm", "lad16cd", "bng_e", "bng_n"]])
ax.axis("off")
fig.patch.set_visible(False)
ax.patch.set_visible(False)
# england
if scale == "e":
  ax.set_xlim([120000, 670000])
  ax.set_ylim([ 00000, 550000])
# closeup
elif scale == "closeup":
  ax.set_xlim([380000, 600000])
  ax.set_ylim([130000, 350000])
# LAD centroids
#ax.plot(gdf.bng_e, gdf.bng_n, "go")
#for item in [fig, ax]:
#  item.patch.set_visible(False)

gdf[~gdf.lad16cd.isin(arclads)].plot(alpha=0.5, edgecolor='k', color='w', ax=ax)
gdf[gdf.lad16cd.isin(arclads)].plot(alpha=0.5, edgecolor='k', color='orange', ax=ax)
gdf[gdf.lad16cd.isin(ctrlads)].plot(alpha=0.5, edgecolor='k', color='r', ax=ax)
plt.show()
#fig.savefig("CaMKOx/" + scale + ".png")