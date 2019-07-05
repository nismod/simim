"""Generate economic scenarios from Arc dwellings, employment, GVA data
"""
import pandas as pd


def main():
  scenario_names = ["0-unplanned", "1-new-cities", "2-expansion"]
  arclads = pd.read_csv("data/scenarios/camkox_lads.csv").geo_code.unique()
  baseline = read_data("baseline", arclads)

  for scenario_name in scenario_names:
    # read scenario data
    scenario = read_data(scenario_name, arclads)

    # calculate diff from baseline
    scenario = scenario.join(baseline, lsuffix="_scen", rsuffix="_base")
    scenario["GVA"] = scenario.gva_per_sector_scen - scenario.gva_per_sector_base
    scenario["JOBS"] = scenario.employment_scen - scenario.employment_base
    scenario["HOUSEHOLDS"] = scenario.dwellings_scen - scenario.dwellings_base
    scenario = scenario[
      ["GVA", "JOBS", "HOUSEHOLDS"]
    ].reset_index().rename({"lad_uk_2016": "GEOGRAPHY_CODE", "timestep": "YEAR"}, axis=1)

    # output households-only scenario
    scenario[["YEAR", "GEOGRAPHY_CODE", "HOUSEHOLDS"]].to_csv(
      "data/scenarios/scenario{}__h.csv".format(scenario_name), index=False)

    # output households-gva-jobs scenarios
    scenario.to_csv("data/scenarios/scenario{}__gjh.csv".format(scenario_name), index=False)


def read_data(key, arclads):
  df_gva = pd.read_csv("data/arc/arc_gva__{}.csv".format(key))
  df_emp = pd.read_csv("data/arc/arc_employment__{}.csv".format(key))
  df_dwl = pd.read_csv("data/arc/arc_dwellings__{}.csv".format(key))

  # merge to single dataframe
  df = df_gva.merge(
    df_emp, on=["timestep", "lad_uk_2016"], how="left"
  ).merge(
    df_dwl, on=["timestep", "lad_uk_2016"], how="left"
  )

  # filter to include only Arc LADs
  df = df[df.lad_uk_2016.isin(arclads)].set_index(["timestep", "lad_uk_2016"])

  return df

if __name__ == '__main__':
  main()
