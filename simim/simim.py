#!/usr/bin/env python3

import os
import numpy as np
import pandas as pd
import geopandas
import matplotlib.pyplot as plt
import simim.data_apis as data_apis
import simim.scenario as scenario
import simim.models as models

import ukpopulation.utils as ukpoputils

from simim.utils import get_named_values, calc_distances, access_weighted_sum

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

def _get_delta(fetch_func, name, year, geogs):
  data_prev = fetch_func(year - 1, geogs).rename({name: name + "_PREV"},axis=1)
  data = fetch_func(year, geogs)
  data = data.merge(data_prev, on="GEOGRAPHY_CODE")
  data[name + "_DELTA"] = data[name] - data[name + "_PREV"]
  return data[["GEOGRAPHY_CODE", name + "_DELTA"]]

def _apply_delta(dataset, factor_name, relative=False):
  if relative:
    dataset[ORIGIN_PREFIX + factor_name] *= dataset[ORIGIN_PREFIX + factor_name + "_DELTA"]
    dataset[DESTINATION_PREFIX + factor_name] *= dataset[DESTINATION_PREFIX + factor_name + "_DELTA"]
  else:
    dataset[ORIGIN_PREFIX + factor_name] += dataset[ORIGIN_PREFIX + factor_name + "_DELTA"]
    dataset[DESTINATION_PREFIX + factor_name] += dataset[DESTINATION_PREFIX + factor_name + "_DELTA"]
  dataset.drop([ORIGIN_PREFIX + factor_name + "_DELTA", DESTINATION_PREFIX + factor_name + "_DELTA"], axis=1, inplace=True)
  return dataset

def _compute_derived_factors(dataset):

  # Calculate some derived factors
  # dataset[ORIGIN_PREFIX + "PEOPLE_DENSITY"] = dataset[ORIGIN_PREFIX + "PEOPLE"] / dataset.O_AREA_KM2
  # dataset[ORIGIN_PREFIX + "HOUSEHOLDS_DENSITY"] = dataset[ORIGIN_PREFIX + "HOUSEHOLDS"] / dataset.O_AREA_KM2
  # dataset[ORIGIN_PREFIX + "HOUSEHOLDS_SIZE"] = dataset[ORIGIN_PREFIX + "HOUSEHOLDS"] / dataset.O_PEOPLE
  # dataset[ORIGIN_PREFIX + "JOBS_DENSITY"] = dataset[ORIGIN_PREFIX + "JOBS"] / dataset.O_AREA_KM2

  # dataset[DESTINATION_PREFIX + "PEOPLE_DENSITY"] = dataset[DESTINATION_PREFIX + "PEOPLE"] / dataset.D_AREA_KM2
  # dataset[DESTINATION_PREFIX + "HOUSEHOLDS_DENSITY"] = dataset[DESTINATION_PREFIX + "HOUSEHOLDS"] / dataset.D_AREA_KM2
  # dataset[DESTINATION_PREFIX + "HOUSEHOLDS_SIZE"] = dataset[DESTINATION_PREFIX + "HOUSEHOLDS"] / dataset.D_PEOPLE
  # dataset[DESTINATION_PREFIX + "JOBS_DENSITY"] = dataset[DESTINATION_PREFIX + "JOBS"] / dataset.D_AREA_KM2

  # London's high GVA does not prevent migration so we artificially reduce it
  dataset[DESTINATION_PREFIX + "GVA_EX_LONDON"] = dataset[DESTINATION_PREFIX + "GVA"]
  min_gva = min(dataset[DESTINATION_PREFIX + "GVA"])
  dataset.loc[dataset.D_GEOGRAPHY_CODE.str.startswith("E09"), DESTINATION_PREFIX + "GVA_EX_LONDON"] = min_gva

  # # Experiment with reducing London's JOBS-ACCESS
  # dataset[DESTINATION_PREFIX + "JOBS_EX_LONDON"] = dataset[DESTINATION_PREFIX + "JOBS"]
  # dataset[ORIGIN_PREFIX + "JOBS_EX_LONDON"] = dataset[ORIGIN_PREFIX + "JOBS"]
  # min_jobs = min(dataset[DESTINATION_PREFIX + "JOBS"])
  # dataset.loc[dataset.D_GEOGRAPHY_CODE.str.startswith("E09"), DESTINATION_PREFIX + "JOBS_EX_LONDON"] = min_jobs
  # dataset.loc[dataset.O_GEOGRAPHY_CODE.str.startswith("E09"), ORIGIN_PREFIX + "JOBS_EX_LONDON"] = min_jobs
  # dataset = access_weighted_sum(dataset, "JOBS_EX_LONDON", "ACCESSIBILITY")

  # D_JOBS_ACCESS applies accessibility to OD trips which provides a measure of job
  # accessibility at destination. This attemptes to capture the possibility that a LAD may be
  # made a more attractive place to live by increased jobs in a nearby LAD
  dataset = access_weighted_sum(dataset, "JOBS", "ACCESSIBILITY")
  # dataset.to_csv("debug_post-compute-derived-factors.csv")
  return dataset

def simim(params):
  # Differentiate between origin and destination values
  # This allows use of e.g. derived values (e.g. population density) to be both an emitter and an attractor. Absolute values cannot (->singular matrix)
  # enure arrays
  if isinstance(params["emitters"], str):
    params["emitters"] = [params["emitters"]]
  if isinstance(params["attractors"], str):
    params["attractors"] = [params["attractors"]]

  params["emitters"] = [ORIGIN_PREFIX + e for e in params["emitters"]]
  params["attractors"] = [DESTINATION_PREFIX + e for e in params["attractors"]]

  # optional OD scenario - for e.g. transport accessibility between pairs of zones
  if "od_scenario" in params:
    od_scenario_filename = os.path.join(params["scenario_dir"], params["od_scenario"])
  else:
    od_scenario_filename = None

  scenario_data = scenario.Scenario(
    os.path.join(params["scenario_dir"], params["scenario"]),
    params["emitters"] + params["attractors"],
    od_scenario_filename)

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

  # census merged LAD migrations are duplicated, so proportion them accoring to 2011 population ratios,
  # converting back to nearest integer (model requires int observations)
  cmpops = input_data.get_people(2011, ["E09000001","E09000033"])
  city_westminster_ratio = cmpops[cmpops.GEOGRAPHY_CODE == "E09000001"].PEOPLE.values[0] / cmpops.PEOPLE.sum()
  cmpops = input_data.get_people(2011, ["E06000052", "E06000053"])
  scilly_cornwall_ratio = cmpops[cmpops.GEOGRAPHY_CODE == "E06000053"].PEOPLE.values[0] / cmpops.PEOPLE.sum()
  # (adjustments for Westminster/City of London and Cornwall/Scilly Isles)
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == "E09000001", "MIGRATIONS"] *= city_westminster_ratio
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == "E09000033", "MIGRATIONS"] *= 1 - city_westminster_ratio
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E09000001", "MIGRATIONS"] *= city_westminster_ratio
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E09000033", "MIGRATIONS"] *= 1 - city_westminster_ratio
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == "E06000053", "MIGRATIONS"] *= scilly_cornwall_ratio
  od_2011.loc[od_2011.O_GEOGRAPHY_CODE == "E06000052", "MIGRATIONS"] *= 1 - scilly_cornwall_ratio
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E06000053", "MIGRATIONS"] *= scilly_cornwall_ratio
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E06000052", "MIGRATIONS"] *= 1 - scilly_cornwall_ratio
  od_2011.MIGRATIONS = od_2011.MIGRATIONS.round().astype(int)

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

  # use start year if defined in config, otherwise default to economics scenario start year
  start_year = params.get("start_year", input_data.economic_data.YEAR.min())
  if start_year > scenario_data.timeline()[0]:
    raise RuntimeError("start year for model run cannot be after start year of scenario")
  # use end year if defined in config, otherwise default to SNPP end year (up to 2039 due to Wales SNPP still being 2014-based)
  end_year = params.get("end_year", input_data.snpp.max_year("en"))
  if end_year < scenario_data.timeline()[0]:
    raise RuntimeError("end year for model run cannot be before start year of scenario")

  # assemble initial model
  baseline_snpp = input_data.get_people(start_year, geogs)
  snhp = input_data.get_households(start_year, geogs)

  jobs = input_data.get_jobs(start_year, geogs)
  gva = input_data.get_gva(start_year, geogs)

  # Merge attractors and emitters *all at both origin AND destination*
  dataset = _merge_factor(od_2011, baseline_snpp, ["PEOPLE"])
  #print(dataset.head())
  dataset = _merge_factor(dataset, snhp, ["HOUSEHOLDS"])
  dataset = _merge_factor(dataset, jobs, ["JOBS"])
  dataset = _merge_factor(dataset, gva, ["GVA"])

  # add accessibility to dataset
  dataset = dataset.merge(input_data.get_accessibility(dataset), on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"])

  # compute derived factors...
  # - GVA ex-London
  # - employment accessibility from accessibility and jobs
  # - could include density-derived factors
  dataset = _compute_derived_factors(dataset)
  # dataset.to_csv("debug_dataset-pre-model.csv")

  # constructor checks for no bad values in data
  model = models.Model(params["model_type"],
                       params["model_subtype"],
                       dataset,
                       params["observation"],
                       params["emitters"],
                       params["attractors"],
                       params["cost"])
  # dataset is now sunk into model, delete the original
  del dataset

  # scale migrations by dividing by this factor - assumes model naturally represents this
  # percentage of actual migrations
  migration_scale_factor = 0.08
  if "migration_scale_factor" in params:
    migration_scale_factor = params["migration_scale_factor"]

  emitter_values = get_named_values(model.dataset, params["emitters"])
  attractor_values = get_named_values(model.dataset, params["attractors"])
  # check recalculation matches the fitted values
  assert np.allclose(model.impl.yhat, model(emitter_values, attractor_values))

  rho = np.corrcoef(model.impl.y[:,0], model.impl.yhat)[0,1]
  print("NOTE: overriding model R2")
  model.impl.pseudoR2 = rho**2

  # print the model params
  print("%d data %s/%s Poisson fit:\nR2 = %f, RMSE=%f" % (start_year, params["model_type"], params["model_subtype"], model.impl.pseudoR2, model.impl.SRMSE))
  print("k =", model.k())
  if params["model_type"] == "gravity" or params["model_type"] == "attraction":
    print("       ", params["emitters"])
    print("mu    =", *model.mu())
  if params["model_type"] == "gravity" or params["model_type"] == "production":
    print("       ", params["attractors"])
    print("alpha =", *model.alpha())
  print("beta = %f" % model.beta())

  # main loop
  for year in range(start_year, end_year + 1):

    # if scenario compute changed migrations
    if year in scenario_data.timeline():
      # compute pre-scenario model migrations
      emitter_values = get_named_values(model.dataset, params["emitters"])
      attractor_values = get_named_values(model.dataset, params["attractors"])
      model_migrations_pre_scenario = model(emitter_values, attractor_values)

      # NOTE derived factors update here under scenario; previously derived values done with
      # baseline updates below

      # apply scenario and recompute derived factors
      model.dataset = scenario_data.apply(model.dataset, year)
      model.dataset = _compute_derived_factors(model.dataset)
      model.check_dataset()

      # re-evaluate model and record changes
      emitter_values = get_named_values(model.dataset, params["emitters"])
      attractor_values = get_named_values(model.dataset, params["attractors"])
      model_migrations_post_scenario = model(emitter_values, attractor_values)

      # scale migrations according to observed value
      model.dataset["CHANGED_MIGRATIONS"] = model.dataset["MIGRATIONS"] * (model_migrations_post_scenario / model_migrations_pre_scenario - 1.0)
      # model.dataset.to_csv("debug_dataset-post-scenario-{}.csv".format(year))
    else:
      model.dataset["CHANGED_MIGRATIONS"] = 0

    #ox = ox.append(model.dataset[(model.dataset.O_GEOGRAPHY_CODE == model.dataset.D_GEOGRAPHY_CODE) & (model.dataset.O_GEOGRAPHY_CODE == "E07000178")])

    # compute migration inflows and outflow changes
    delta = pd.DataFrame({"o_lad16cd": model.dataset.O_GEOGRAPHY_CODE,
                          "d_lad16cd": model.dataset.D_GEOGRAPHY_CODE,
                          "delta": model.dataset.CHANGED_MIGRATIONS})

    # upscale delta by mover percentage at origin
    delta = pd.merge(delta, movers, left_on="o_lad16cd", right_index=True)
    # TODO reinstate if necessary
    delta["delta"] /= migration_scale_factor
    # delta["delta"] /= delta["MIGRATION_RATE"]
    delta = delta.drop(["PEOPLE", "MIGRATIONS", "MIGRATION_RATE"], axis=1)

    # remove in-LAD migrations and sum
    o_delta = delta.groupby("d_lad16cd").sum().reset_index().rename({"d_lad16cd": "lad16cd", "delta": "o_delta"}, axis=1)
    d_delta = delta.groupby("o_lad16cd").sum().reset_index().rename({"o_lad16cd": "lad16cd", "delta": "d_delta"}, axis=1)
    delta = o_delta.merge(d_delta)
    # compute net migration change
    delta["net_delta"] = delta.o_delta - delta.d_delta

    #print(delta[delta["lad16cd"].isin(scenario_data.geographies())])
    print("Change in migrations to scenario region: %.0f" % delta[delta["lad16cd"].isin(scenario_data.geographies())]["net_delta"].sum())

    # add to results and to model dataset
    custom_snpp = baseline_snpp.merge(model.dataset[["O_GEOGRAPHY_CODE", "O_PEOPLE"]].drop_duplicates(), left_on="GEOGRAPHY_CODE", right_on="O_GEOGRAPHY_CODE") \
      .rename({"PEOPLE": "PEOPLE_SNPP", "O_PEOPLE": "PEOPLE"}, axis=1)
    custom_snpp = custom_snpp.drop(["O_GEOGRAPHY_CODE"], axis=1) \
      .merge(delta, left_on="GEOGRAPHY_CODE", right_on="lad16cd").drop(["lad16cd", "o_delta", "d_delta"], axis=1)
    custom_snpp["PEOPLE"] += custom_snpp["net_delta"]
    custom_snpp.drop("net_delta", axis=1, inplace=True)

    model.dataset = model.dataset.drop({"O_PEOPLE", "D_PEOPLE"}, axis=1) \
      .merge(custom_snpp[["GEOGRAPHY_CODE", "PEOPLE"]].rename({"PEOPLE": "O_PEOPLE"}, axis=1), left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE") \
      .merge(custom_snpp[["GEOGRAPHY_CODE", "PEOPLE"]].rename({"PEOPLE": "D_PEOPLE"}, axis=1), left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE") \
      .drop({"GEOGRAPHY_CODE_x", "GEOGRAPHY_CODE_y"}, axis=1)

    # TODO IDEA: merge emitters/attractors back on to custom_snpp for output/comparison as calculated

    input_data.append_output(custom_snpp, year)

    # now update baselines for following year, unless we are in the final year
    if year < end_year:
      # persist data from model but take relative SNPP change
      baseline_snpp_prev = input_data.get_people(year, geogs).rename({"PEOPLE": "PEOPLE_PREV"},axis=1)
      baseline_snpp = input_data.get_people(year+1, geogs)
      baseline_snpp = baseline_snpp.merge(baseline_snpp_prev, on="GEOGRAPHY_CODE")
      # relative delta
      baseline_snpp["PEOPLE_DELTA"] = baseline_snpp["PEOPLE"] / baseline_snpp["PEOPLE_PREV"]
      model.dataset = _merge_factor(model.dataset, baseline_snpp[["GEOGRAPHY_CODE", "PEOPLE_DELTA"]], ["PEOPLE_DELTA"])
      model.dataset = _apply_delta(model.dataset, "PEOPLE", relative=True)

      # absolute deltas
      snhp = _get_delta(input_data.get_households, "HOUSEHOLDS", year+1, geogs)
      model.dataset = _merge_factor(model.dataset, snhp, ["HOUSEHOLDS_DELTA"])
      model.dataset = _apply_delta(model.dataset, "HOUSEHOLDS")

      jobs = _get_delta(input_data.get_jobs, "JOBS", year+1, geogs)
      model.dataset = _merge_factor(model.dataset, jobs, ["JOBS_DELTA"])
      model.dataset = _apply_delta(model.dataset, "JOBS")

      gva = _get_delta(input_data.get_gva, "GVA", year+1, geogs)
      model.dataset = _merge_factor(model.dataset, gva, ["GVA_DELTA"])
      model.dataset = _apply_delta(model.dataset, "GVA")

      # derived factors
      model.dataset = _compute_derived_factors(model.dataset)

  input_data.summarise_output(scenario_data)

  if "odmatrix" in params and params["odmatrix"] is True:
    input_data.write_odmatrix(model.dataset[["O_GEOGRAPHY_CODE","D_GEOGRAPHY_CODE","O_PEOPLE","D_PEOPLE","MIGRATIONS","CHANGED_MIGRATIONS"]])

  return model, input_data, delta
