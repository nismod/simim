#!/usr/bin/env python3

""" 
Creates a GB-wide lookup table of OA-LSOA-MSOA-LAD-CMLAD from scattered datasets
For Scotland LSOA = DataZone, MSOA=Intermediate zone, LAD=Council Area
CMLAD refers to census-merged LAD codes for E&W
"""
import pandas as pd

# TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
lookup = pd.read_csv("../../UrbCap/data/cache/LAD_lookup.csv")
lookup.rename({"GEOGRAPHY_NAME": "LAD_NAME", "GEOGRAPHY": "LAD_NOMIS", "GEOGRAPHY_CODE": "LAD", "CM_GEOGRAPHY": "LAD_CM_NOMIS", "CM_GEOGRAPHY_CODE": "LAD_CM"}, axis=1, inplace=True)
print(lookup.head())


sc_geog_lookup = pd.read_csv("../microsimulation/cache/sc_lookup.csv") \
                  .rename({"OutputArea": "OA","DataZone": "LSOA","InterZone": "MSOA", "Council": "LAD"}, axis=1)
geog_lookup = pd.read_csv("../../Mistral/persistent_data/oa2011codes.csv.gz", compression="infer") \
                  .rename({"oa": "OA","lsoa": "LSOA","msoa": "MSOA", "la": "LAD"}, axis=1) \
                  .append(sc_geog_lookup)

print(geog_lookup.head())
print(geog_lookup.LAD.unique())

geog_lookup = geog_lookup.merge(lookup, how="left")

# use LAD code for CM LAD code in Scotland
geog_lookup.loc[geog_lookup.LAD.str.startswith("S"), "LAD_CM"] = geog_lookup[geog_lookup.LAD.str.startswith("S")].LAD

# From https://www.nrscotland.gov.uk/files//geography/2011-census-indexes-csv.zip
sc_lad_names = pd.read_csv("../../Mistral/persistent_data/COUNCIL AREA 2011 LOOKUP.csv").rename({"CouncilArea2011Code": "LAD"}, axis=1) 
geog_lookup = geog_lookup.merge(sc_lad_names[["LAD", "CouncilArea2011Name"]], how="left")
geog_lookup.loc[geog_lookup.LAD_NAME.isnull(), "LAD_NAME"] = geog_lookup[geog_lookup.LAD_NAME.isnull()].CouncilArea2011Name 
geog_lookup.drop("CouncilArea2011Name", axis=1, inplace=True)
print(len(geog_lookup))
print(len(geog_lookup.LAD.unique()))
print(geog_lookup.head())
print(geog_lookup[geog_lookup.LAD.str.startswith("S")].head())


filename="../microsimulation/persistent_data/gb_geog_lookup.csv.gz"
geog_lookup.to_csv(filename, compression="gzip")
print("written to " + filename)


