""" helpers for sim prototypes """

import os
import argparse
import numpy as np
import pandas as pd
import requests
import hashlib
import zipfile
import re
import geopandas as gpd
from scipy.stats.stats import pearsonr 

def md5hash(string):
  m = hashlib.md5()
  m.update(string.encode('utf-8'))
  return m.hexdigest()

def get_data(local, remote):
  if os.path.isfile(local):
    data = pd.read_csv(local)
  else:
    data = pd.read_csv(remote)
    data.to_csv(local, index=False)
  return data

def get_shapefile(zip_url, cache_dir):
  local_zipfile = os.path.join(cache_dir, md5hash(zip_url) + ".zip")
  if not os.path.isfile(local_zipfile):
    response = requests.get(zip_url)
    response.raise_for_status()
    with open(local_zipfile, 'wb') as fd:
      for chunk in response.iter_content(chunk_size=1024):
        fd.write(chunk)
    print("downloaded OK")
  else: 
    print("using cached data: %s" % local_zipfile)
  
  zip = zipfile.ZipFile(local_zipfile)
  #print(zip.namelist())
  # find a shapefile in the zip...
  regex = re.compile(".*\.shp$")
  f = filter(regex.match, zip.namelist())
  shapefile = str(next(f))
  # can't find a way of reading this directly into geopandas
  zip.extractall(path=cache_dir)
  return gpd.read_file(os.path.join(cache_dir, shapefile))

def r2(fitted, actual):
  return pearsonr(fitted, actual)[0] ** 2

def rmse(fitted, actual):
  return np.sqrt(np.mean((fitted - actual) ** 2))

# def get_args():
#   parser = argparse.ArgumentParser(description="sim demo")
#   parser.add_argument("-g", "--graphs", action='store_const', const=True, default=False, help="show graphics")
#   parser.add_argument("-s", "--subset", action='store_const', const=True, default=False, help="subset data")
#   parser.add_argument("-w", "--write", action='store_const', const=True, default=False, help="save fitted data")

#   return parser.parse_args()


