#!/usr/bin/env python3
"""
generate a scenario
"""

import pandas as pd

def main(params):
  ctrlads = ["E07000178", "E06000042", "E07000008"]
  arclads = ["E07000181", "E07000180", "E07000177", "E07000179", "E07000004", "E06000032", "E06000055", "E06000056", "E07000011", "E07000012"]
  camkox = ctrlads.copy()
  camkox.extend(arclads)

  # increase household spaces in CaMKOx uniformly by 260000 over 5 years
  years = range(2020,2025)

  scenario = pd.DataFrame({"GEOGRAPHY_CODE": [], "YEAR": [], "HOUSEHOLDS": []})

  hh_per_year_per_lad = 260000 / 13 / 5
  for year in years:
    scenario = scenario.append(pd.DataFrame({"GEOGRAPHY_CODE": camkox, "YEAR": year, "HOUSEHOLDS": hh_per_year_per_lad}))

  print(scenario)
  scenario.to_csv("./scenario1.csv", index=False)

if __name__ == "__main__":

  main(None)