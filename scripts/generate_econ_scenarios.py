"""Generate economic scenarios from Ca-MK-Ox Arc dwellings, employment, GVA data
"""
import pandas as pd


def main():
  scenario_names = ["0-unplanned", "1-new-cities", "2-expansion", "3-new-cities23", "4-expansion23"]
  arclads = pd.read_csv("data/scenarios/camkox_lads.csv").geo_code.unique()
  baseline = read_data("baseline", arclads)

  for scenario_name in scenario_names:
    # read scenario data
    scenario = read_data(scenario_name, arclads)

    # calculate diff from baseline, rounded as int
    scenario = scenario.join(baseline, lsuffix="_scen", rsuffix="_base")
    scenario["GVA"] = (scenario.gva_per_sector_scen - scenario.gva_per_sector_base)
    scenario["JOBS"] = (scenario.employment_scen - scenario.employment_base)
    scenario["HOUSEHOLDS"] = (scenario.dwellings_scen - scenario.dwellings_base)
    scenario = scenario[
      ["GVA", "JOBS", "HOUSEHOLDS"]
    ].reset_index().rename({"lad_uk_2016": "GEOGRAPHY_CODE", "timestep": "YEAR"}, axis=1)

    # Calculate year-on-year differences
    years = list(reversed(sorted(scenario.YEAR.unique())))

    df = scenario.pivot(index="GEOGRAPHY_CODE", columns="YEAR", values=["GVA", "JOBS", "HOUSEHOLDS"])
    for i, year in enumerate(years):
      for key in ["GVA", "JOBS", "HOUSEHOLDS"]:
        if year == scenario.YEAR.min():
          df[key][year] = 0
        else:
          df[key][year] = (df[key][year] - df[key][years[i + 1]])

    unpivot = df[["GVA"]].reset_index() \
        .melt(id_vars="GEOGRAPHY_CODE") \
        [["GEOGRAPHY_CODE", "YEAR"]]

    for key in ["GVA", "JOBS", "HOUSEHOLDS"]:
      col = df[[key]].reset_index() \
        .melt(id_vars="GEOGRAPHY_CODE") \
        [["GEOGRAPHY_CODE", "YEAR", "value"]] \
        .rename(columns={"value": key})        
      unpivot = unpivot.merge(col, on=["GEOGRAPHY_CODE", "YEAR"])
    
    scenario = unpivot
    scenario["GVA"] = scenario["GVA"].round(6)
    scenario["JOBS"] = (scenario["JOBS"] * 1000).round().astype(int)  # convert from 1000s jobs to jobs
    scenario["HOUSEHOLDS"] = scenario["HOUSEHOLDS"].round().astype(int)
    
    # Filter to include only 2019 and later
    scenario = scenario[scenario.YEAR >= 2019]

    # output households-only scenario
    scenario[["YEAR", "GEOGRAPHY_CODE", "HOUSEHOLDS"]].to_csv(
      "data/scenarios/scenario{}__h.csv".format(scenario_name), index=False)

    # output households-gva-jobs scenarios
    scenario.to_csv("data/scenarios/scenario{}__gjh.csv".format(scenario_name), index=False)


def read_data(key, arclads):
  """Read csvs and merge to single dataframe
  """
  # HACK hard-code match for economics scenarios against 23k dwellings scenarios
  if key == "3-new-cities23":
    econ_key = "1-new-cities"
  elif key == "4-expansion23":
    econ_key = "2-expansion"
  else:
    econ_key = key

  df_gva = pd.read_csv("data/arc/arc_gva__{}.csv".format(econ_key))
  df_emp = pd.read_csv("data/arc/arc_employment__{}.csv".format(econ_key))
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
