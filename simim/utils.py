""" helpers for sim prototypes """
import os
import argparse
import numpy as np
import pandas as pd
import hashlib
import json
from scipy.stats.stats import pearsonr
from scipy.spatial.distance import squareform, pdist

def md5hash(string):
  m = hashlib.md5()
  m.update(string.encode('utf-8'))
  return m.hexdigest()

def get_named_values(dataset, colnames, prefix=""):
  """ Returns a list of Series from dataset, optionally prefixed when modified original values are needed"""
  if not isinstance(colnames, list):
    return dataset[prefix+colnames]
  else:
    return [dataset[prefix+colname] for colname in colnames]


def get_data(local, remote):
  if os.path.isfile(local):
    data = pd.read_csv(local)
  else:
    data = pd.read_csv(remote)
    data.to_csv(local, index=False)
  return data

def calc_distances(gdf):
  # for now makes assumptions about column names and units
  dists = pd.DataFrame(squareform(pdist(pd.DataFrame({"e": gdf.bng_e, "n": gdf.bng_n}))), columns=gdf.lad16cd.unique(), index=gdf.lad16cd.unique())
  # turn matrix into table
  dists = dists.stack().reset_index().rename({"level_0": "orig", "level_1": "dest", 0: "DISTANCE"}, axis=1)
  # convert to km
  dists.DISTANCE = dists.DISTANCE / 1000.0
  return dists

def access_weighted_sum(dataset, colname, access_colname):
  # (travel) access-weighted sum of factor at destination
  # access-to-x[d] = Sum over o { access[o,d] * x[o] }
  new_colname = "D_{}_{}".format(colname, access_colname)

  # access to x[o] for each o,d
  dataset[new_colname] = dataset["O_" + colname] * dataset[access_colname]
  # sum over o - grouping by d
  wsum = dataset[["D_GEOGRAPHY_CODE", new_colname]].groupby("D_GEOGRAPHY_CODE").sum().reset_index()

  # merge back
  dataset = dataset.merge(wsum, on="D_GEOGRAPHY_CODE") \
    .drop(new_colname + "_x", axis=1) \
    .rename({new_colname + "_y": new_colname}, axis=1)

  return dataset

def r2(fitted, actual):
  return pearsonr(fitted, actual)[0] ** 2

def rmse(fitted, actual):
  return np.sqrt(np.mean((fitted - actual) ** 2))

def od_matrix(dataset, value_col, o_col, d_col):
  return np.nan_to_num(dataset[[value_col, o_col, d_col]].set_index([o_col, d_col]).unstack().values)

def get_config():
  parser = argparse.ArgumentParser(description="spatial interaction model of internal migration")
  parser.add_argument("-c", "--config", required=True, type=str, metavar="config-file", help="the model configuration file (json). See config/default.json")

  args = parser.parse_args()

  with open(args.config) as config_file:
    params = json.load(config_file)
  return params

# throws if problem with inputs, warns for untested settings
def validate_config(params):
  if params["coverage"] !="GB":
    print('WARNING: Coverage other than "GB" has not been properly tested, proceed with caution')

  if params["model_type"] == "gravity" and "GEOGRAPHY_CODE" in params["emitters"]:
    raise ValueError("Gravity (unconstrained) model requires numeric values for emission factor(s)")
  if params["model_type"] == "production" and not (params["emitters"] == ["GEOGRAPHY_CODE"] or params["emitters"] == "GEOGRAPHY_CODE"):
    raise ValueError("production (constrained) model must use GEOGRAPHY_CODE for emission factor")
