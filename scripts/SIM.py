#!/usr/bin/env python3

import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx
import simim.data as data
import simim.models as models
import simim.visuals as visuals

# import statsmodels.api as sm
# #import statsmodels.formula.api as smf

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

import ukcensusapi.Nomisweb as Nomisweb
import ukcensusapi.NRScotland as NRScotland
import ukcensusapi.NISRA as NISRA

from simim.utils import get_shapefile, calc_distances, get_config

import ukpopulation.utils as ukpoputils

def main(params):

  do_graphs = True

  coverage = { "EW": ukpoputils.EW, "GB": ukpoputils.GB, "UK": ukpoputils.UK}.get(params["coverage"]) 
  if not coverage:
    raise RuntimeError("invalid coverage: %s" % params["coverage"])

  census_ew = Nomisweb.Nomisweb(params["cache_dir"])
  census_sc = NRScotland.NRScotland(params["cache_dir"])
  census_ni = NISRA.NISRA(params["cache_dir"])

  od_2011 = data.get_od(census_ew)

  # # CMLAD codes...
  # print("E06000048" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # print("E06000057" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # # TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
  lookup = pd.read_csv("../microsimulation/persistent_data/gb_geog_lookup.csv.gz")

  # TODO need to remap old NI codes 95.. to N... ones

  # only need the CMLAD->LAD mapping
  lad_lookup = lookup[["LAD_CM", "LAD"]].drop_duplicates().reset_index(drop=True)
  od_2011 = od_2011.merge(lad_lookup, how='left', left_on="ADDRESS_ONE_YEAR_AGO_CODE", right_on="LAD_CM") \
    .rename({"LAD": "O_GEOGRAPHY_CODE"}, axis=1).drop(["LAD_CM"], axis=1)
  od_2011 = od_2011.merge(lad_lookup, how='left', left_on="USUAL_RESIDENCE_CODE", right_on="LAD_CM") \
   .rename({"LAD": "D_GEOGRAPHY_CODE", "OBS_VALUE": "MIGRATIONS"}, axis=1).drop(["LAD_CM"], axis=1)

  # ensure blanks arising from Sc/NI not being in lookup are reinstated from original data
  od_2011.loc[pd.isnull(od_2011.O_GEOGRAPHY_CODE), "O_GEOGRAPHY_CODE"] = od_2011.ADDRESS_ONE_YEAR_AGO_CODE[pd.isnull(od_2011.O_GEOGRAPHY_CODE)]
  od_2011.loc[pd.isnull(od_2011.D_GEOGRAPHY_CODE), "D_GEOGRAPHY_CODE"] = od_2011.USUAL_RESIDENCE_CODE[pd.isnull(od_2011.D_GEOGRAPHY_CODE)]

  od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isnull()) & (~od_2011.O_GEOGRAPHY_CODE.isnull())]
  od_2011.drop(["ADDRESS_ONE_YEAR_AGO_CODE", "USUAL_RESIDENCE_CODE"], axis=1, inplace=True)

  # TODO adjustments for Westminster/City or London and Cornwall/Scilly Isles
  # for now just remove City & Scilly
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E09000001") & (od_2011.D_GEOGRAPHY_CODE != "E09000001")]
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E06000053") & (od_2011.D_GEOGRAPHY_CODE != "E06000053")]

  geogs = od_2011.O_GEOGRAPHY_CODE.unique()

  # people
  #p_2011 = data.get_people(census_ew, census_sc, census_ni if do_NI else None)
  p_2011 = data.get_people(params["start_year"], geogs, params["cache_dir"])

  hh_2011 = data.get_households(census_ew, census_sc, census_ni if ukpoputils.NI in coverage else None)

  # get distances (url is GB ultra generalised clipped LAD boundaries/centroids)
  url = "https://opendata.arcgis.com/datasets/686603e943f948acaa13fb5d2b0f1275_4.zip?outSR=%7B%22wkid%22%3A27700%2C%22latestWkid%22%3A27700%7D"
  gdf = get_shapefile(url, params["cache_dir"])

  dists = calc_distances(gdf)
  print(dists.head())

  # merge with OD
  od_2011 = od_2011.merge(dists, how="left", left_on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"], right_on=["orig", "dest"]).drop(["orig", "dest"], axis=1)

  # Merge population *at origin*
  od_2011 = od_2011.merge(p_2011, how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
  # Merge households *at destination*
  od_2011 = od_2011.merge(hh_2011, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
  print(od_2011.head())

  odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values
  #print(odmatrix.shape)

  # remove O=D rows
  od_2011 = od_2011[od_2011.O_GEOGRAPHY_CODE != od_2011.D_GEOGRAPHY_CODE]

  # set epsilon dist for O=D rows
  #od_2011.loc[od_2011.O_GEOGRAPHY_CODE == od_2011.D_GEOGRAPHY_CODE, "DISTANCE"] = 1e-0

  if ukpoputils.NI not in coverage:
    ni = ['95TT', '95XX', '95OO', '95GG', '95DD', '95QQ', '95ZZ', '95VV', '95YY', '95CC',
          '95II', '95NN', '95AA', '95RR', '95MM', '95LL', '95FF', '95BB', '95SS', '95HH',
          '95EE', '95PP', '95UU', '95WW', '95KK', '95JJ']
    od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isin(ni)) & (~od_2011.D_GEOGRAPHY_CODE.isin(ni))]
    odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values

  #od_2011.to_csv("od2011.csv", index=False)
  # print(od_2011[od_2011.DISTANCE.isnull()])
  # stop

  print("model: %s[IGNORED] (%s)" % (params["model_type"], params["model_subtype"]))

# TODO model class takes entire DF (+O/D column(s)) and adds its yhat as a column
#  od_model = 

  gravity = models.Model("gravity", params["model_subtype"], od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values)

  print("Unconstrained Poisson Fitted R2 = %f" % gravity.impl.pseudoR2)
  print("Unconstrained Poisson Fitted RMSE = %f" % gravity.impl.SRMSE)

  # model = Production(od_2011.MIGRATIONS.values, od_2011.O_GEOGRAPHY_CODE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model_subtype)
  attr = models.Model("attraction", params["model_subtype"], od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.DISTANCE.values)
  doubly = models.Model("doubly", params["model_subtype"], od_2011.MIGRATIONS.values, od_2011.O_GEOGRAPHY_CODE.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.DISTANCE.values)

  # visualise
  if do_graphs:
    #fig, [[ax1, ax01], [ax10, ax11]] = plt.subplots(nrows=2, ncols=2, figsize=(10, 10), sharex=False, sharey=False)
    #fig, [ax1, ax01] = plt.subplots(nrows=1, ncols=2, figsize=(16, 10), sharex=False, sharey=False)
    v = visuals.Visual(2,3)
    ax00 = v.axes[0,0]
    model_od = v.axes[0,1] 
    ax01 = v.axes[1,0]
    ax10 = v.axes[1,1]
    ax11 = v.axes[1,2]
    #fig.suptitle("UK LAD SIMs using population as emitter, households as attractor")
    ax00.set_title("OD matrix (displaced log scale)")
    ax00.imshow(np.log(odmatrix+1), cmap=plt.get_cmap('Greens'))
    ax00.xaxis.set_visible(False)
    ax00.yaxis.set_visible(False)

    ax01.set_title("Unconstrained fit: R^2=%.2f" % gravity.impl.pseudoR2)
    ax01.plot(od_2011.MIGRATIONS, gravity.impl.yhat, "b.")

    ax10.set_title("Attraction constrained fit: R^2=%.2f" % attr.impl.pseudoR2)
    ax10.plot(od_2011.MIGRATIONS, attr.impl.yhat, "k.")

    ax11.set_title("Doubly constrained fit: R^2=%.2f" % doubly.impl.pseudoR2)
    ax11.plot(od_2011.MIGRATIONS, doubly.impl.yhat, "r.")

    #ax10.set_title("Migration vs origin population")
    #ax10.plot(od_2011.PEOPLE, od_2011.MIGRATIONS, "k.")

    # ax11.set_title("Migration vs destination households")
    # ax11.plot(od_2011.HOUSEHOLDS, od_2011.MIGRATIONS, "r.")
    v.show()
    #fig.savefig("doc/img/sim_basic.png", transparent=True)

  ybar = gravity(od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values)

if __name__ == "__main__":
  
  main(get_config())