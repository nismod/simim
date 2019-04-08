
import pandas as pd

import ukpopulation.snhpdata as SNHPData
import ukpopulation.utils #as utils


snhp_e = pd.read_csv("data/ons_hh_e_2016-2041.csv").drop([str(y) for y in range(2001,2014)], axis=1)
snhp_w = pd.read_csv("data/hh_w_2014-2039.csv").drop(["Unnamed: 0", "Unnamed: 1"], axis=1)

snhp_s = SNHPData.SNHPData("../microsimulation/cache").data[ukpopulation.utils.SC]

snhp_e = snhp_e.groupby("CODE").sum().reset_index().rename({"CODE": "GEOGRAPHY_CODE"}, axis=1)
snhp_e = snhp_e[snhp_e.GEOGRAPHY_CODE.str.startswith("E0")]
#print(snhp_e)

snhp_w = snhp_w.groupby("GEOGRAPHY_CODE").sum().reset_index()
#print(snhp_w)

#print(snhp_s)

snhp = pd.concat([snhp_e, snhp_w, snhp_s], ignore_index=True, sort=False)

snhp.to_csv("./snhp.csv")