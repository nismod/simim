#!/usr/bin/env python3
"""Convert outputs to use as smif scenarios, extending with MYE for 2011-2015 and SNPP for NI

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
  lads = pd.read_csv('./data/lad_nmcd_changes.csv')
  lad_cds = list(lads.lad16cd.unique())
  pop_mye = get_mye(lad_cds)
  pop_snpp = get_snpp(lad_cds)
  baseline = pd.concat([pop_mye, pop_snpp], axis=0)
  baseline.population = baseline.population.astype(int)
  baseline.to_csv(os.path.join(output_dir, 'arc_population__baseline.csv'), index=False)

  # add baseline pre-2016 and in Northern Ireland to simim scenarios
  addition = baseline[(baseline.timestep < 2016) | baseline.lad_uk_2016.str.startswith('N')]

  # read, rename, add baseline, output ready for smif
  output_files = list(glob.glob(os.path.join(output_dir, 'simim_*.csv')))
  for output_file in output_files:
    scenario = load_simim_output(output_file)
    scenario = pd.concat([scenario, addition], axis=0, sort=True)
    scenario.population = scenario.population.astype(int)

    fname = "arc_population__{}".format(
      os.path.basename(output_file).replace('simim_gravity_ppp_', ''))
    scenario.to_csv(os.path.join(output_dir, fname), index=False)


def get_mye(lad_cds):
  mye = MYEData()
  years = range(2011, 2017)
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


def load_simim_output(filepath):
  df = rename_columns(pd.read_csv(filepath)).drop('PEOPLE_SNPP', axis=1)
  return df


def rename_columns(df):
  return df.rename(columns={
    'GEOGRAPHY_CODE': 'lad_uk_2016',
    'PROJECTED_YEAR_NAME': 'timestep',
    'PEOPLE': 'population',
    'OBS_VALUE': 'population'
  })


if __name__ == "__main__":
  params = get_config()
  main(params)
