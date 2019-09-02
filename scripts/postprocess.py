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
  non_arc = baseline[~baseline.lad_uk_2016.isin(arc_lads.geo_code)].copy()

  baseline_dwl = pd.read_csv("./data/arc/arc_dwellings__baseline.csv")
  baseline = baseline.merge(baseline_dwl, on=["timestep", "lad_uk_2016"])
  arc15 = baseline[
    baseline.lad_uk_2016.isin(arc_lads.geo_code) & (baseline.timestep == base_year)].copy()
  arc15['RELATIVE_DELTA'] = 1

  # read, rename, add baseline, output ready for smif
  output_files = list(glob.glob(os.path.join(output_dir, "simim_*.csv")))
  dfs = []

  # new cities (23k/30k dwellings per year)
  # new settlements: directly from [dwellings * average people per household]
  # where pph is calculated per-LAD from 2015 numbers
  arc15['pph'] = arc15.population / arc15.dwellings

  for key in ('1-new-cities', '3-new-cities23'):
    scenario_key = '{}-from-dwellings'.format(key)
    print(scenario_key)

    scenario, arc_only = calculate_from_base_year_ppd(
      key, arc15, non_arc, output_dir, base_year, arc_lads)

    scenario = prepare_for_output(scenario)
    fname = "arc_population__{}.csv".format(scenario_key)
    scenario.to_csv(os.path.join(output_dir, fname), index=False)

    arc_only['scenario'] = scenario_key
    dfs.append(arc_only)

  # all scenarios, using simim outputs scaled to meet 'expected' total Arc population
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
    scenario, arc_only = scale(scenario, baseline, arc_lads)
    scenario = scenario[scenario.timestep > base_year]
    scenario = rename_columns(scenario)
    scenario = pd.concat(
      [scenario, addition], axis=0, sort=True
    )

    scenario = prepare_for_output(scenario)
    fname = "arc_population__{}.csv".format(key)
    scenario.to_csv(os.path.join(output_dir, fname), index=False)

    arc_only['scenario'] = key
    dfs.append(arc_only)

  # concat summary
  summary = pd.concat(dfs, axis=0, sort=True)
  summary = summary[summary.timestep.isin([2015, 2030, 2050])]

  # calculate summary if dwellings follow population
  for key in ('0-unplanned', '1-new-cities', '2-expansion', '3-new-cities23', '4-expansion23'):
    scenario_key = '{}-dwellings-after'.format(key)
    print(scenario_key)

    arc_only = summary[summary.scenario == key].copy()
    arc_only = arc_only.drop('pph', axis=1)
    arc_only = arc_only.merge(arc15[['lad_uk_2016','pph']], on=['lad_uk_2016'], how='left')
    arc_only.dwellings = arc_only.scaled_population / arc_only.pph

    arc_only['scenario'] = scenario_key
    summary = summary.append(arc_only, sort=True)


  summary['scaled_pph'] = summary.scaled_population / summary.dwellings
  pivot = summary.pivot_table(index=['lad_uk_2016', 'lad16nm', 'timestep'], columns=['scenario'])
  pivot.to_csv(os.path.join(output_dir, "summarise_simim_population.csv"))


def calculate_from_base_year_ppd(key, arc15, non_arc, output_dir, base_year, arc_lads):
  # construct filename
  prefix = 'simim_gravity_ppp_scenario'
  suffix = '__gjh_D_HOUSEHOLDS-D_JOBS_ACCESSIBILITY-D_GVA_EX_LONDON__od_rail_b1__0.06.csv'
  fname = os.path.join(output_dir, '{}{}{}'.format(prefix, key, suffix))

  assert len(arc15) == len(arc_lads), ("LADs", len(arc15), len(arc_lads))

  # load and filter to arc only, after 2015
  df = load_simim_output(fname, '1-new-cities')
  df = df[df.timestep > base_year]
  df = df[df.lad_uk_2016.isin(arc_lads.geo_code)].copy()

  # join 2015 people-per-dwelling, calculate population
  df = df.merge(arc15[['lad_uk_2016','pph']], on=['lad_uk_2016'], how='left')
  df.population = df.dwellings * df.pph
  df = df.append(arc15, sort=True)
  df['people_scale_factor'] = 1
  df['scaled_population'] = df.population

  # include base year
  scenario = pd.concat([df[['timestep', 'lad_uk_2016', 'population']], non_arc], axis=0, sort=True)
  return scenario, df


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

  # copy for later comparative use
  arc_only = dataset.copy()

  dataset = dataset[["timestep","lad_uk_2016","scaled_population"]] \
    .rename(columns={"scaled_population": "population"})

  other_scenario = scenario[~scenario.lad_uk_2016.isin(arc_lads.geo_code)] \
    [["timestep", "lad_uk_2016", "population"]]

  dataset = pd.concat([
    dataset,
    other_scenario
  ], axis=0, sort=True)

  return dataset, arc_only


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
