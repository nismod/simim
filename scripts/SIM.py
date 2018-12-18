#!/usr/bin/env python3

import os
import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx
import simim.data_apis as data_apis
import simim.scenario as scenario
import simim.models as models
import simim.visuals as visuals

import ukpopulation.utils as ukpoputils

from simim.utils import get_named_values, calc_distances, od_matrix, get_config

# ctrlads = ["E07000178", "E06000042", "E07000008"]
# arclads = ["E07000181", "E07000180", "E07000177", "E07000179", "E07000004", "E06000032", "E06000055", "E06000056", "E07000011", "E07000012"]

def main(params):

  data = data_apis.Instance(params)
  scenario_data = scenario.Scenario(params["scenario"])

  if params["base_projection"] != "ppp":
    raise NotImplementedError("TODO variant projections...")

  od_2011 = data.get_od()

  # # CMLAD codes...
  # print("E06000048" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # print("E06000057" in od_2011.USUAL_RESIDENCE_CODE.unique())
  # # TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
  # TODO need to remap old NI codes 95.. to N... ones

  lad_lookup = data.get_lad_lookup() #pd.read_csv("../microsimulation/persistent_data/gb_geog_lookup.csv.gz")

  # TODO need to remap old NI codes 95.. to N... ones

  # only need the CMLAD->LAD mapping
  #lad_lookup = lookup[["LAD_CM", "LAD"]].drop_duplicates().reset_index(drop=True)
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

  # get distances (url is GB ultra generalised clipped LAD boundaries/centroids)
  url = "https://opendata.arcgis.com/datasets/686603e943f948acaa13fb5d2b0f1275_4.zip?outSR=%7B%22wkid%22%3A27700%2C%22latestWkid%22%3A27700%7D"
  gdf = data.get_shapefile(url)

  dists = calc_distances(gdf)
  # merge with OD
  od_2011 = od_2011.merge(dists, how="left", left_on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"], right_on=["orig", "dest"]).drop(["orig", "dest"], axis=1)

  # set minimum cost dist for O=D rows
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == od_2011.D_GEOGRAPHY_CODE, "DISTANCE"] = 1e-0
  #print(od_2011.head())

  # TODO 
  # 26 LGDs -> 11 in 2014 with N09000... codes
  # see https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&ved=2ahUKEwiXzuiWu5rfAhURCxoKHYH1A9YQFjAAegQIBRAC&url=http%3A%2F%2Fwww.ninis2.nisra.gov.uk%2FDownload%2FPopulation%2FBirths%2520to%2520Mothers%2520from%2520Outside%2520Northern%2520Ireland%2520%25202013%2520Provisional%2520(administrative%2520geographies).xlsx&usg=AOvVaw3ZI3EDJAJxtsFQVRMEX37C
  if ukpoputils.NI not in data.coverage:
    ni = ['95TT', '95XX', '95OO', '95GG', '95DD', '95QQ', '95ZZ', '95VV', '95YY', '95CC',
          '95II', '95NN', '95AA', '95RR', '95MM', '95LL', '95FF', '95BB', '95SS', '95HH',
          '95EE', '95PP', '95UU', '95WW', '95KK', '95JJ']
    od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isin(ni)) & (~od_2011.D_GEOGRAPHY_CODE.isin(ni))]
    odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values

  timeline = scenario_data.timeline()

  custom_variant = pd.DataFrame()

  # ensure base dataset is sorted so that the mu/alphas for the constrained models are interpreted correctly
  od_2011.sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"], inplace=True)

  # loop from snpp start to scenario start
  for year in range(data.snpp.min_year("en"), timeline[0]):
    snpp = data.get_people(year, geogs)
    snpp["net_delta"] = 0
    data.append_output(snpp, year)
    print("pre-scenario %d" % year)

  # loop over scenario years (up to 2039 due to Wales SNPP still being 2014-based)
  for year in range(scenario_data.timeline()[0], data.snpp.max_year("en") - 1):
    # people
    snpp = data.get_people(year, geogs)

    # TODO use projections
    snhp = data.get_households(year, geogs)

    jobs = data.get_jobs(year, geogs)

    # Merge population *at origin*
    dataset = od_2011
    dataset = dataset.merge(snpp, how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
    # Merge households & jobs *at destination*
    dataset = dataset.merge(snhp, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
    dataset = dataset.merge(jobs, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)

    # save dataset for testing
    # dataset.to_csv("./tests/data/testdata.csv.gz", index=False, compression="gzip")
    # break

    odmatrix = od_matrix(dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")

    model = models.Model(params["model_type"], 
                         params["model_subtype"], 
                         dataset, 
                         params["observation"], 
                         params["emitters"],
                         params["attractors"], 
                         params["cost"])
    #prod = models.Model("production", params["model_subtype"], dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", "HOUSEHOLDS", "DISTANCE")

    emitter_values = get_named_values(dataset, params["emitters"])
    attractor_values = get_named_values(dataset, params["attractors"])

    assert np.allclose(model.impl.yhat, model(emitter_values, attractor_values))

    #assert np.allclose(prod.impl.yhat, prod(xd=dataset.HOUSEHOLDS))

    print("%d data %s/%s Poisson fit R2 = %f, RMSE=%f" % (year, params["model_type"], params["model_subtype"], model.impl.pseudoR2, model.impl.SRMSE))

    model_odmatrix = od_matrix(model.dataset, "MODEL_MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")

    # apply scenario to dataset
    dataset = scenario_data.apply(dataset, year)
    
    changed_attractor_values = get_named_values(dataset, params["attractors"], prefix="CHANGED_")

    # TODO generalise...
    # re-evaluate model and record changes
    dataset["CHANGED_MIGRATIONS"] = model(dataset.PEOPLE.values, changed_attractor_values)
    # print(model.dataset[dataset.MIGRATIONS != dataset.CHANGED_MIGRATIONS])

    # construct new OD matrix
    changed_odmatrix = od_matrix(dataset, "CHANGED_MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")
    delta_odmatrix = changed_odmatrix - model_odmatrix

    # compute migration inflows and outflow changes 
    delta = pd.DataFrame({"o_lad16cd": dataset.O_GEOGRAPHY_CODE, 
                          "d_lad16cd": dataset.D_GEOGRAPHY_CODE, 
                          "delta": -dataset.CHANGED_MIGRATIONS + model.dataset.MODEL_MIGRATIONS})
    # remove in-LAD migrations and sun
    o_delta = delta.groupby("o_lad16cd").sum().reset_index().rename({"o_lad16cd": "lad16cd", "delta": "o_delta"}, axis=1)
    d_delta = delta.groupby("d_lad16cd").sum().reset_index().rename({"d_lad16cd": "lad16cd", "delta": "d_delta"}, axis=1)
    delta = o_delta.merge(d_delta)
    # compute net migration change
    delta["net_delta"] = delta.o_delta - delta.d_delta

    # add to results
    snpp = snpp.merge(delta, left_on="GEOGRAPHY_CODE", right_on="lad16cd").drop(["lad16cd", "o_delta", "d_delta"], axis=1)
    #print(snpp.head())
    data.append_output(snpp, year)

    #break

  print("writing custom SNPP variant data to %s" % data.output_file)
  data.write_output()

  # visualise
  if params["graphics"]:
    # fig.suptitle("UK LAD SIMs using population as emitter, households as attractor")
    v = visuals.Visual(2,3)

    v.scatter((0,0), dataset.MIGRATIONS, model.impl.yhat, "b.", title="%d %s migration model fit: R^2=%.2f" \
      % (year, params["model_type"], model.impl.pseudoR2))
    v.line((0,0), [0,max(dataset.MIGRATIONS)], [0,max(dataset.MIGRATIONS)], "k", linewidth=0.25)

    # N.Herts = "E07000099"
    # Cambridge "E07000008"
    lad = "E07000178" # Oxford
    c = data.custom_snpp_variant[data.custom_snpp_variant.GEOGRAPHY_CODE == lad]
    v.line((0,1), c.YEAR, c.PEOPLE, "k", label="baseline", xlabel="Year", ylabel="Population", title="Impact of scenario on population (%s)" % lad)
    v.line((0,1), c.YEAR, c.PEOPLE + c.net_delta, "r", label="scenario")

    # TODO change in population...
    # v.polygons((0,2), gdf, xlim=[120000, 670000], ylim=[0, 550000], linewidth=0.25, edgecolor="darkgrey", facecolor="lightgrey")
    # v.polygons((0,2), gdf[gdf.lad16cd.isin(arclads)], xlim=[120000, 670000], ylim=[0, 550000], linewidth=0.25, edgecolor="darkgrey", facecolor="orange")
    # v.polygons((0,2), gdf[gdf.lad16cd.isin(ctrlads)], xlim=[120000, 670000], ylim=[0, 550000], linewidth=0.25, edgecolor="darkgrey", facecolor="red")
    gdf = gdf.merge(delta)
    # net emigration in blue
    net_out = gdf[gdf.net_delta < 0.0]
    v.polygons((0,2), net_out, title="%s migration model implied impact on population" % params["model_type"], xlim=[120000, 670000], ylim=[0, 550000], 
      values=-net_out.net_delta, clim=(0, np.max(-net_out.net_delta)), cmap="Blues", edgecolor="darkgrey", linewidth=0.25)
    # net immigration in red
    net_in = gdf[gdf.net_delta >= 0.0] 
    v.polygons((0,2), net_in, xlim=[120000, 670000], ylim=[0, 550000], 
      values=net_in.net_delta, clim=(0, np.max(net_in.net_delta)), cmap="Reds", edgecolor="darkgrey", linewidth=0.25)

    #print(gdf[gdf.net_delta >= 0.0])

    v.matrix((1,0), np.log(odmatrix+1), cmap="Greens", title="Actual OD matrix (displaced log scale)")
    v.matrix((1,1), np.log(model_odmatrix+1), cmap="Greys", title="%s model OD matrix (displaced log scale)" % params["model_type"])
    # we get away with log here as no values are -ve
    v.matrix((1,2), np.log(1+delta_odmatrix), cmap="Oranges", title="%s model perturbed OD matrix delta" % params["model_type"])
    #absmax = max(np.max(delta_od),-np.min(delta_od))
    #v.matrix((1,2), delta_od, 'RdBu', title="Gravity model perturbed OD matrix delta", clim=(-absmax/50,absmax/50))

    v.show()
    #v.to_png("doc/img/sim_basic.png")

if __name__ == "__main__":
  
  main(get_config())