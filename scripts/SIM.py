#!/usr/bin/env python3

import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx
import simim.data as data

# import statsmodels.api as sm
# #import statsmodels.formula.api as smf

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

import ukcensusapi.Nomisweb as Nomisweb
import ukcensusapi.NRScotland as NRScotland
import ukcensusapi.NISRA as NISRA

from simim.utils import get_shapefile, calc_distances, get_config

# TODO ukpopulation

def main(params):

  do_graphs = True
  do_NI = params["coverage"] == "UK"

  census_ew = Nomisweb.Nomisweb(params["cache_dir"])
  census_sc = NRScotland.NRScotland(params["cache_dir"])
  census_ni = NISRA.NISRA(params["cache_dir"])

  od_2011 = data.get_od(census_ew)

  # # CMLAD codes...
  # print("E06000048" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # print("E06000057" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # # TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
  lookup = pd.read_csv("../microsimulation/persistent_data/gb_geog_lookup.csv.gz")

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

  # #print(od_2011.O_GEOGRAPHY_CODE.unique())
  # print(od_2011.D_GEOGRAPHY_CODE.unique())
  # print(len(od_2011.O_GEOGRAPHY_CODE.unique()))
  # print(len(od_2011.D_GEOGRAPHY_CODE.unique()))

  # TODO adjustments for Westminster/City or London and Cornwall/Scilly Isles
  # for now just remove City & Scilly
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E09000001") & (od_2011.D_GEOGRAPHY_CODE != "E09000001")]
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E06000053") & (od_2011.D_GEOGRAPHY_CODE != "E06000053")]

  # people
  p_2011 = data.get_people(census_ew, census_sc, census_ni if do_NI else None)

  hh_2011 = data.get_households(census_ew, census_sc, census_ni if do_NI else None)


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

  if not do_NI:
    ni = ['95TT', '95XX', '95OO', '95GG', '95DD', '95QQ', '95ZZ', '95VV', '95YY', '95CC',
          '95II', '95NN', '95AA', '95RR', '95MM', '95LL', '95FF', '95BB', '95SS', '95HH',
          '95EE', '95PP', '95UU', '95WW', '95KK', '95JJ']
    od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isin(ni)) & (~od_2011.D_GEOGRAPHY_CODE.isin(ni))]
    odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values

  #od_2011.to_csv("od2011.csv", index=False)
  # print(od_2011[od_2011.DISTANCE.isnull()])
  # stop

  # pysal impl
  model = "pow"
  print("model: " + model)
  gravity = Gravity(od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model)
  #print(gravity.params)
  # TODO this formula is wrong?
  k = gravity.params[0]
  mu = gravity.params[1]
  alpha = gravity.params[2]
  beta = gravity.params[3]
  if model == "pow":
    est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values
  else:
    est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * np.exp(od_2011.DISTANCE * beta)).values

  print("Unconstrained Poisson Fitted R2 = %f" % gravity.pseudoR2)
  print("Unconstrained Poisson Fitted RMSE = %f" % gravity.SRMSE)
  print(np.mean(est_unc - gravity.yhat))
  print(np.sqrt(np.mean((est_unc - gravity.yhat)**2)))

  #perturb
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] = od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
  pert_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)

  # can only affect rows with the perturbed destination
  print(np.count_nonzero(pert_unc - est_unc)/len(est_unc)) # =1/378

  # # re-fit model
  # gravity_bumped = Gravity(od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model)
  # print(gravity.params)
  # print(gravity_bumped.params)
  # k = gravity_bumped.params[0]
  # mu = gravity_bumped.params[1]
  # alpha = gravity_bumped.params[2]
  # beta = gravity_bumped.params[3]
  # bump_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # print("Bumped Unconstrained Poisson Fitted R2 = %f" % gravity_bumped.pseudoR2)
  # print("Bumped Unconstrained Poisson Fitted RMSE = %f" % gravity_bumped.SRMSE)

  # print(np.count_nonzero(bump_unc - est_unc)/len(est_unc))

  # Unconstrained Poisson Fitted R2 = 0.575711
  # Unconstrained Poisson Fitted RMSE = 64.298780

  # alpha = np.append(np.array(0.0), attr.params[2:-1])
  # beta = attr.params[-1]
  # #T_ij = exp(k + mu ln(V_i) + alpha_j + beta * ln?(D_ij))
  # # est_attr = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # print(len(alpha), len(od_2011.D_GEOGRAPHY_CODE.unique()))

  # T0 = np.exp(k + mu * np.log(od_2011.PEOPLE.values[0]) + alpha[0] + np.log(od_2011.DISTANCE.values[0]) * beta)
  # print(T0, attr.yhat[0])
  # #print(attr.yhat)

  # Attraction constrained model
  model = "pow"
  attr = Attraction(od_2011.MIGRATIONS.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.PEOPLE.values, od_2011.DISTANCE.values, model)
  # k = attr.params[0]
  # mu = attr.params[1]

  print("Attr-constrained Poisson Fitted R2 = %f" % attr.pseudoR2)
  print("Attr-constrained Poisson Fitted RMSE = %f" % attr.SRMSE)

  doubly = Doubly(od_2011.MIGRATIONS.values, od_2011.O_GEOGRAPHY_CODE.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.DISTANCE.values, 'exp')
  print("Doubly-constrained Poisson Fitted R2 = %f" % doubly.pseudoR2)
  print("Doubly-constrained Poisson Fitted RMSE = %f" % doubly.SRMSE)

  # visualise
  if do_graphs:
    fig, [[ax1, ax2], [ax3, ax4]] = plt.subplots(nrows=2, ncols=2, figsize=(10, 10), sharex=False, sharey=False)
    #fig, [ax1, ax2] = plt.subplots(nrows=1, ncols=2, figsize=(16, 10), sharex=False, sharey=False)

    #fig.suptitle("UK LAD SIMs using population as emitter, households as attractor")
    ax1.set_title("OD matrix (displaced log scale)")
    ax1.imshow(np.log(odmatrix+1), cmap=plt.get_cmap('Greens'))
    #ax2.imshow(np.log(1+gravity.yhat), cmap=plt.get_cmap('Greens'))
    #ax2.imshow(gravity.yhat-odmatrix, cmap=plt.get_cmap('Greens'))
    ax1.xaxis.set_visible(False)
    ax1.yaxis.set_visible(False)

    ax2.set_title("Unconstrained fit: R^2=%.2f" % gravity.pseudoR2)
    ax2.plot(od_2011.MIGRATIONS, gravity.yhat, "b.")

    ax3.set_title("Attraction constrained fit: R^2=%.2f" % attr.pseudoR2)
    ax3.plot(od_2011.MIGRATIONS, attr.yhat, "k.")

    ax4.set_title("Doubly constrained fit: R^2=%.2f" % doubly.pseudoR2)
    ax4.plot(od_2011.MIGRATIONS, doubly.yhat, "r.")

    #ax3.set_title("Migration vs origin population")
    #ax3.plot(od_2011.PEOPLE, od_2011.MIGRATIONS, "k.")

    # ax4.set_title("Migration vs destination households")
    # ax4.plot(od_2011.HOUSEHOLDS, od_2011.MIGRATIONS, "r.")
    plt.tight_layout()
    plt.show()
    #fig.savefig("doc/img/sim_basic.png", transparent=True)

if __name__ == "__main__":
  
  main(get_config())