#!/usr/bin/env python3
"""Convert outputs to use as smif scenarios, extending with MYE for 2011-2015 and SNPP for NI

Scales simim outputs to meet the baseline population-per-household on average across the Arc,
which varies according to the dwelling scenarios. This ensures the total Arc population reaches
the scenario target we want to explore, while using simim's outputs to give the proportional
allocation of population migrating to and within the Arc.

E.g. usage:

  $ cat config.json
  {
    "output_dir": "./data/output"
  }

  $ python scripts/postprocess.py -c config.json

"""
import glob
import os
import sys

import pandas as pd
from simim.utils import get_config
from ukpopulation.myedata import MYEData
from ukpopulation.nppdata import NPPData
from ukpopulation.snppdata import SNPPData


def main(params):
  if "output_dir" not in params:
    print("No 'output_dir' provided in config")
    sys.exit()

  output_dir = params["output_dir"]
  if not os.path.isdir(output_dir):
    print("No output directory found %s" % output_dir)
    sys.exit()

  # get baseline 2011-2050, all UK
  lads = pd.read_csv("./data/lad_nmcd_changes.csv")
  arc_lads = pd.read_csv("./data/scenarios/camkox_lads.csv")
  lad_cds = list(lads.lad16cd.unique())
  pop_mye = get_mye(lad_cds)
  pop_snpp = get_snpp(lad_cds)
  baseline = pd.concat([pop_mye, pop_snpp], axis=0)

  baseline = prepare_for_output(baseline)
  baseline.to_csv(os.path.join(output_dir, "arc_population__baseline.csv"), index=False)

  # add baseline pre-2016 and in Northern Ireland to simim scenarios
  base_year = 2015
  addition = baseline[
    (baseline.timestep <= base_year) | baseline.lad_uk_2016.str.startswith("N")
  ].copy()

  baseline_dwl = pd.read_csv("./data/arc/arc_dwellings__baseline.csv")
  baseline = baseline.merge(baseline_dwl, on=["timestep", "lad_uk_2016"])

  # read, rename, add baseline, output ready for smif
  output_files = list(glob.glob(os.path.join(output_dir, "simim_*.csv")))
  for output_file in output_files:
    key = os.path.basename(
      output_file
    ).replace(
      "simim_gravity_ppp_scenario", ""
    ).replace(
      "__gjh_D_HOUSEHOLDS-D_JOBS_ACCESSIBILITY-D_GVA_EX_LONDON__od_rail_b1__0.06.csv", ""
    )
    print(key)

    scenario = load_simim_output(output_file, key)
    scenario = scale(scenario, baseline, arc_lads)
    scenario = scenario[scenario.timestep > base_year]
    scenario = rename_columns(scenario)
    scenario = pd.concat(
      [scenario, addition], axis=0, sort=False
    )

    scenario = prepare_for_output(scenario)
    fname = "arc_population__{}.csv".format(key)
    scenario.to_csv(os.path.join(output_dir, fname), index=False)


def scale(scenario, baseline, arc_lads):
  # stitch scenario and baseline together
  scenario = scenario.copy()
  scenario["scenario"] = "scenario"
  baseline = baseline.copy()
  baseline["scenario"] = "baseline"

  full = pd.concat([scenario, baseline], axis=0, sort=True)
  # filter to Arc only
  dataset = full[full.lad_uk_2016.isin(arc_lads.geo_code)].copy()
  # calculate people per household
  dataset["pph"] = dataset.population / dataset.dwellings
  # group to summarise
  summary = dataset.groupby(["timestep","scenario"]).sum()
  summary["pph"] = summary.population / summary.dwellings
  # merge on baseline
  summary = summary.reset_index()
  summary = summary.merge(
          summary[summary.scenario == "baseline"][["timestep","pph"]],
          on="timestep", how="left", suffixes=("","_baseline"))
  # calculate expected population from scenario households and baseline people-per-household
  summary["expected_population"] = summary.dwellings * summary.pph_baseline
  # calculate scale factor
  summary["people_scale_factor"] = summary.expected_population / summary.population
  # merge summary back to main dataset
  dataset = dataset.merge(
      summary[["timestep","scenario", "people_scale_factor"]],
      on=["timestep","scenario"], how="left")
  # calculate scaled population
  dataset["scaled_population"] = dataset.population * dataset.people_scale_factor
  # rename, filter, concatenate back into rest of scenario output
  dataset = dataset[dataset.scenario != "baseline"]
  dataset = dataset[["timestep","lad_uk_2016","scaled_population"]] \
    .rename(columns={"scaled_population": "population"})

  other_scenario = scenario[~scenario.lad_uk_2016.isin(arc_lads.geo_code)] \
    [["timestep", "lad_uk_2016", "population"]]

  dataset = pd.concat([
    dataset,
    other_scenario
  ], axis=0, sort=True)
  return dataset


def get_mye(lad_cds):
  mye = MYEData()
  years = range(2015, 2017)
  pop_mye = rename_columns(mye.aggregate(["GENDER", "C_AGE"], lad_cds, years))
  return pop_mye


def get_snpp(lad_cds):
  snpp = SNPPData()
  snpp_years = range(2017, 2040)
  extra_years = range(2040, 2051)

  pop_snpp = rename_columns(snpp.aggregate(["GENDER", "C_AGE"], lad_cds, snpp_years))

  npp = NPPData()
  pop_ex = rename_columns(snpp.extrapolagg(["GENDER", "C_AGE"], npp, lad_cds, extra_years))

  pop_snpp = rename_columns(pop_snpp)
  return pd.concat([pop_ex, pop_snpp], axis=0)


def load_simim_output(filepath, scenario_key):
  df_pop = rename_columns(pd.read_csv(filepath).drop("PEOPLE_SNPP", axis=1))
  df_dwl = pd.read_csv("./data/arc/arc_dwellings__{}.csv".format(scenario_key))
  df = df_pop.merge(df_dwl, on=["timestep", "lad_uk_2016"])

  return df


def prepare_for_output(df):
  df.population = df.population.astype(int)
  return df.sort_values(
      ["timestep", "lad_uk_2016"]
    )[
      ["timestep", "lad_uk_2016", "population"]
    ]


def rename_columns(df):
  return df.rename(columns={
    "GEOGRAPHY_CODE": "lad_uk_2016",
    "PROJECTED_YEAR_NAME": "timestep",
    "PEOPLE": "population",
    "OBS_VALUE": "population"
  })


if __name__ == "__main__":
  params = get_config()
  main(params)
