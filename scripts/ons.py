#!/usr/bin/env python3

import json
import requests

URL = "https://api.beta.ons.gov.uk/v1/datasets"

#dataset = "mid-year-pop-est"
dataset = "cpih01"

response = requests.get(URL)
response.raise_for_status()
datasets = response.json()

for item in datasets["items"]:
  #print(item['id'])
  if item["id"] == dataset:
    #print(json.dumps(item, indent=2)) #["0"])
    url = item["links"]["latest_version"]["href"]
    print(url)
    response = requests.get(url)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))

# come back to this later... its nowhere near being usable
# https://digitalblog.ons.gov.uk/2018/05/24/using-the-new-beta-ons-api/

# this sint working at all
# https://developer.ons.gov.uk/office-for-national-statistics-api/reference/listing-of-datasets/listing-of-datasets

#https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/5/observations?time=*&aggregate=cpih1dim1A0&geography=K02000001

#https://api.beta.ons.gov.uk/v1/datasets/mid-year-pop-est/editions/time-series/versions/1/observations?time=2016&sex=0&age=*&geography=E09000001
