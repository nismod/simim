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

import ukpopulation.utils as ukpoputils

from simim.utils import get_named_values, calc_distances, dist_weighted_sum

ORIGIN_PREFIX = "O_"
DESTINATION_PREFIX = "D_"

def _merge_factor(dataset, data, factors):
  omapping = dict(zip(factors, [ORIGIN_PREFIX + f for f in factors]))
  dataset = dataset.merge(data[["GEOGRAPHY_CODE"] + factors], how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1) \
    .rename(omapping, axis=1)
  dmapping = dict(zip(factors, [DESTINATION_PREFIX + f for f in factors]))
  dataset = dataset.merge(data[["GEOGRAPHY_CODE"] + factors], how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1) \
    .rename(dmapping, axis=1)
  return dataset


def simim(params):

  #pd.set_option('display.max_columns', None)

  # Differentiate between origin and destination values
  # This allows use of e.g. derived values (e.g. population density) to be both an emitter and an attractor. Absolute values cannot (->singular matrix)
  # enure arrays
  if isinstance(params["emitters"], str):
    params["emitters"] = [params["emitters"]]
  if isinstance(params["attractors"], str):
    params["attractors"] = [params["attractors"]]

  params["emitters"] = [ORIGIN_PREFIX + e for e in params["emitters"]]
  params["attractors"] = [DESTINATION_PREFIX + e for e in params["attractors"]]

  scenario_data = scenario.Scenario(os.path.join(params["scenario_dir"], params["scenario"]), params["emitters"] + params["attractors"])

  input_data = data_apis.Instance(params)

  if params["base_projection"] != "ppp":
    raise NotImplementedError("TODO variant projections...")

  od_2011 = input_data.get_od()

  lad_lookup = input_data.get_lad_lookup()

  # only need the CMLAD->LAD mapping
  od_2011 = od_2011.merge(lad_lookup, how='left', left_on="ADDRESS_ONE_YEAR_AGO_CODE", right_on="LAD_CM") \
    .rename({"LAD": ORIGIN_PREFIX + "GEOGRAPHY_CODE"}, axis=1).drop(["LAD_CM"], axis=1)
  od_2011 = od_2011.merge(lad_lookup, how='left', left_on="USUAL_RESIDENCE_CODE", right_on="LAD_CM") \
    .rename({"LAD": DESTINATION_PREFIX + "GEOGRAPHY_CODE", "OBS_VALUE": "MIGRATIONS"}, axis=1).drop(["LAD_CM"], axis=1)

  # ensure blanks arising from Sc/NI not being in lookup are reinstated from original data
  od_2011.loc[pd.isnull(od_2011.O_GEOGRAPHY_CODE), "O_GEOGRAPHY_CODE"] = od_2011.ADDRESS_ONE_YEAR_AGO_CODE[pd.isnull(od_2011.O_GEOGRAPHY_CODE)]
  od_2011.loc[pd.isnull(od_2011.D_GEOGRAPHY_CODE), "D_GEOGRAPHY_CODE"] = od_2011.USUAL_RESIDENCE_CODE[pd.isnull(od_2011.D_GEOGRAPHY_CODE)]

  od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isnull()) & (~od_2011.O_GEOGRAPHY_CODE.isnull())]
  od_2011.drop(["ADDRESS_ONE_YEAR_AGO_CODE", "USUAL_RESIDENCE_CODE"], axis=1, inplace=True)

  # TODO census merged LAD adjustments for Westminster/City of London and Cornwall/Scilly Isles
  # for now just remove City & Scilly
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E09000001") & (od_2011.D_GEOGRAPHY_CODE != "E09000001")]
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E06000053") & (od_2011.D_GEOGRAPHY_CODE != "E06000053")]

  # get distances (url is GB ultra generalised clipped LAD boundaries/centroids)
  url = "https://opendata.arcgis.com/datasets/686603e943f948acaa13fb5d2b0f1275_4.zip?outSR=%7B%22wkid%22%3A27700%2C%22latestWkid%22%3A27700%7D"

  shapefile = input_data.get_shapefile(url)
  dists = calc_distances(shapefile)
  # merge dists with OD
  od_2011 = od_2011.merge(dists, how="left", left_on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"], right_on=["orig", "dest"]).drop(["orig", "dest"], axis=1)
  # add areas (converting from square metres (not hectares!) to square km)
  od_2011 = od_2011.merge(shapefile[["lad16cd", "st_areasha"]], left_on="O_GEOGRAPHY_CODE", right_on="lad16cd").drop("lad16cd", axis=1).rename({"st_areasha": "O_AREA_KM2"}, axis=1)
  od_2011.loc[:,"O_AREA_KM2"] *= 1e-6
  od_2011 = od_2011.merge(shapefile[["lad16cd", "st_areasha"]], left_on="D_GEOGRAPHY_CODE", right_on="lad16cd").drop("lad16cd", axis=1).rename({"st_areasha": "D_AREA_KM2"}, axis=1)
  od_2011.loc[:,"D_AREA_KM2"] *= 1e-6

  # set minimum cost dist for O=D rows
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == od_2011.D_GEOGRAPHY_CODE, "DISTANCE"] = 1e-0
  #print(od_2011.head())

  # TODO need to remap old NI codes 95.. to N... ones
  # 26 LGDs -> 11 in 2014 with N09000... codes
  # see https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&ved=2ahUKEwiXzuiWu5rfAhURCxoKHYH1A9YQFjAAegQIBRAC&url=http%3A%2F%2Fwww.ninis2.nisra.gov.uk%2FDownload%2FPopulation%2FBirths%2520to%2520Mothers%2520from%2520Outside%2520Northern%2520Ireland%2520%25202013%2520Provisional%2520(administrative%2520geographies).xlsx&usg=AOvVaw3ZI3EDJAJxtsFQVRMEX37C
  if ukpoputils.NI not in input_data.coverage:
    ni = ['95TT', '95XX', '95OO', '95GG', '95DD', '95QQ', '95ZZ', '95VV', '95YY', '95CC',
          '95II', '95NN', '95AA', '95RR', '95MM', '95LL', '95FF', '95BB', '95SS', '95HH',
          '95EE', '95PP', '95UU', '95WW', '95KK', '95JJ']
    od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isin(ni)) & (~od_2011.D_GEOGRAPHY_CODE.isin(ni))]

  geogs = od_2011.O_GEOGRAPHY_CODE.unique()

  # get no of people who moved (by origin) for each LAD - for later use as a scaling factor for migrations
  movers = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE"]].groupby("O_GEOGRAPHY_CODE").sum()
  movers = input_data.get_people(2011, geogs).set_index("GEOGRAPHY_CODE").join(movers)
  # Fudge factor 
  movers["MIGRATION_RATE"] = movers["MIGRATIONS"] / movers["PEOPLE"]

  print("Overall migration rate is %1.2f%%" % (100 * movers["MIGRATIONS"].sum() / movers["PEOPLE"].sum()))

  # # ensure base dataset is sorted so that the mu/alphas for the constrained models are interpreted correctly
  # od_2011.sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"], inplace=True)

  # use start year if defined in config, otherwise default to SNPP start year
  start_year = params.get("start_year", input_data.snpp.min_year("en"))
  if start_year > scenario_data.timeline()[0]:
    raise RuntimeError("start year for model run cannot be after start year of scenario")
  # use end year if defined in config, otherwise default to SNPP end year (up to 2039 due to Wales SNPP still being 2014-based)
  end_year = params.get("end_year", input_data.snpp.max_year("en"))
  if end_year < scenario_data.timeline()[0]:
    raise RuntimeError("end year for model run cannot be before start year of scenario")

  # loop from snpp start to just before scenario start
  for year in range(start_year, scenario_data.timeline()[0]):
    snpp = input_data.get_people(year, geogs)
    # pre-secenario the custom variant is same as the base projection
    snpp["PEOPLE_SNPP"] = snpp.PEOPLE
    input_data.append_output(snpp, year)
    print("pre-scenario %d" % year)

  model = None

  # loop over scenario years to end_year
  for year in range(scenario_data.timeline()[0], end_year + 1): 

    # TODO persist data from model 
    snpp_prev = snpp.rename({"PEOPLE": "PEOPLE_PREV", "PEOPLE_SNPP": "PEOPLE_SNPP_PREV"}, axis=1)
    #print(snpp_prev.head())
    snpp = input_data.get_people(year, geogs).rename({"PEOPLE": "PEOPLE_SNPP"},axis=1)
    snpp = snpp.merge(snpp_prev, on="GEOGRAPHY_CODE")
    snpp["DELTA_SNPP"] = snpp["PEOPLE_SNPP"] / snpp_prev["PEOPLE_SNPP_PREV"]
    snpp["PEOPLE"] = snpp["PEOPLE_PREV"] * snpp["DELTA_SNPP"]

    # TODO SNHP_PREV/DELTA
    snhp = input_data.get_households(year, geogs)

    jobs = input_data.get_jobs(year, geogs)

    gva = input_data.get_gva(year, geogs)

    # Merge attractors and emitters *all at both origin AND destination*
    dataset = _merge_factor(od_2011, snpp, ["PEOPLE", "PEOPLE_SNPP"]).drop("D_PEOPLE_SNPP", axis=1)
    #print(dataset.head())
    dataset = _merge_factor(dataset, snhp, ["HOUSEHOLDS"]) 
    dataset = _merge_factor(dataset, jobs, ["JOBS", "JOBS_PER_WORKING_AGE_PERSON"])
    dataset = _merge_factor(dataset, gva, ["GVA"])

    # distance decay function is exp(-ln(0.5)d/l) ensure half the attraction at distance l
    dataset = dist_weighted_sum(dataset, "D_JOBS", 20.0, lambda l, d: np.exp(np.log(0.5) / l * d))

    # dataset.to_csv("dataset.csv", index=False)
    # exit(1)

    # # Calculate some derived factors
    # dataset[ORIGIN_PREFIX + "PEOPLE_DENSITY"] = dataset[ORIGIN_PREFIX + "PEOPLE"] / dataset.O_AREA_KM2
    # dataset[ORIGIN_PREFIX + "HOUSEHOLDS_DENSITY"] = dataset[ORIGIN_PREFIX + "HOUSEHOLDS"] / dataset.O_AREA_KM2
    # dataset[ORIGIN_PREFIX + "HOUSEHOLDS_SIZE"] = dataset[ORIGIN_PREFIX + "HOUSEHOLDS"] / dataset.O_PEOPLE
    # dataset[ORIGIN_PREFIX + "JOBS_DENSITY"] = dataset[ORIGIN_PREFIX + "JOBS"] / dataset.O_AREA_KM2

    # dataset[DESTINATION_PREFIX + "PEOPLE_DENSITY"] = dataset[DESTINATION_PREFIX + "PEOPLE"] / dataset.D_AREA_KM2
    # dataset[DESTINATION_PREFIX + "HOUSEHOLDS_DENSITY"] = dataset[DESTINATION_PREFIX + "HOUSEHOLDS"] / dataset.D_AREA_KM2
    # dataset[DESTINATION_PREFIX + "HOUSEHOLDS_SIZE"] = dataset[DESTINATION_PREFIX + "HOUSEHOLDS"] / dataset.D_PEOPLE
    # dataset[DESTINATION_PREFIX + "JOBS_DENSITY"] = dataset[DESTINATION_PREFIX + "JOBS"] / dataset.D_AREA_KM2

    # # London's high GVA does not prevent migration so we artificially reduce it
    # dataset[DESTINATION_PREFIX + "GVA_EX_LONDON"] = dataset[DESTINATION_PREFIX + "GVA"]
    # min_gva = min(dataset[DESTINATION_PREFIX + "GVA"])
    # dataset.loc[dataset.D_GEOGRAPHY_CODE.str.startswith("E09"), DESTINATION_PREFIX + "GVA_EX_LONDON"] = min_gva 

    # scale up migrations to full population?
    #dataset.loc[dataset.O_GEOGRAPHY_CODE == dataset.D_GEOGRAPHY_CODE, "MIGRATIONS"] = dataset[dataset.O_GEOGRAPHY_CODE == dataset.D_GEOGRAPHY_CODE].MIGRATIONS * 50

    # save dataset for testing
    #dataset.to_csv("./tests/data/testdata.csv", index=False)

    # check no bad values
    if len(dataset[dataset.isnull().any(axis=1)]) > 0:
      dataset.to_csv("dataset.csv")
    assert len(dataset[dataset.isnull().any(axis=1)]) == 0, "Missing/invalid values in model dataset, dumping to dataset.csv and aborting"

    # print(dataset[(dataset.O_GEOGRAPHY_CODE == dataset.D_GEOGRAPHY_CODE) 
    #             & (dataset.O_GEOGRAPHY_CODE.isin(scenario_data.geographies()))])
    model = models.Model(params["model_type"],
                         params["model_subtype"],
                         dataset,
                         params["observation"],
                         params["emitters"],
                         params["attractors"],
                         params["cost"])
    # dataset is now sunk into model, prevent accidental access by deleting the original
    del dataset

    emitter_values = get_named_values(model.dataset, params["emitters"])
    attractor_values = get_named_values(model.dataset, params["attractors"])
    # check recalculation matches the fitted values
    assert np.allclose(model.impl.yhat, model(emitter_values, attractor_values))

    # print some model params
    print("%d data %s/%s Poisson fit:\nR2 = %f, RMSE=%f" % (year, params["model_type"], params["model_subtype"], model.impl.pseudoR2, model.impl.SRMSE))
    print("k =", model.k())
    if params["model_type"] == "gravity" or params["model_type"] == "attraction":
      print("       ", params["emitters"])
      print("mu    =", *model.mu())
    if params["model_type"] == "gravity" or params["model_type"] == "production":
      print("       ", params["attractors"])
      print("alpha =", *model.alpha())
    print("beta = %f" % model.beta())

    # apply scenario to dataset
    model.dataset = scenario_data.apply(model.dataset, year)

    # TODO recompute derived factors

    # re-evaluate model and record changes
    model.dataset["CHANGED_MIGRATIONS"] = model(emitter_values, attractor_values)

    # model.dataset.to_csv("dataset.csv", index=False)
    # exit(1)

    # compute migration inflows and outflow changes
    delta = pd.DataFrame({"o_lad16cd": model.dataset.O_GEOGRAPHY_CODE,
                          "d_lad16cd": model.dataset.D_GEOGRAPHY_CODE,
                          "delta": -model.dataset.CHANGED_MIGRATIONS + model.dataset.MODEL_MIGRATIONS})
    # upscale delta by mover percentage at origin
    delta = pd.merge(delta, movers, left_on="o_lad16cd", right_index=True) 
    # TODO reinstate if necessary
    #delta["delta"] = delta["delta"] / delta["MIGRATION_RATE"]
    delta = delta.drop(["PEOPLE", "MIGRATIONS", "MIGRATION_RATE"], axis=1)
    
    # remove in-LAD migrations and sum
    o_delta = delta.groupby("o_lad16cd").sum().reset_index().rename({"o_lad16cd": "lad16cd", "delta": "o_delta"}, axis=1)
    d_delta = delta.groupby("d_lad16cd").sum().reset_index().rename({"d_lad16cd": "lad16cd", "delta": "d_delta"}, axis=1)
    delta = o_delta.merge(d_delta)
    # compute net migration change
    delta["net_delta"] = delta.o_delta - delta.d_delta

    print(delta[delta["lad16cd"].isin(scenario_data.geographies())])
    print("Change in migrations to scenario region: %.0f" % delta[delta["lad16cd"].isin(scenario_data.geographies())]["net_delta"].sum())

    # add to results
    snpp = snpp.drop(['PEOPLE_PREV', 'PEOPLE_SNPP_PREV', 'DELTA_SNPP'], axis=1).merge(delta, left_on="GEOGRAPHY_CODE", right_on="lad16cd").drop(["lad16cd", "o_delta", "d_delta"], axis=1)
    snpp["PEOPLE"] += snpp["net_delta"]
    snpp.drop("net_delta", axis=1, inplace=True)
    input_data.append_output(snpp, year)

    print(snpp[snpp.GEOGRAPHY_CODE.isin(scenario_data.geographies())])

    #break

  input_data.summarise_output(scenario_data)

  return model, input_data, delta
