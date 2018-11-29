import numpy as np
import pandas as pd
import geopandas 
import matplotlib.pyplot as plt
import contextily as ctx
from scipy.spatial.distance import squareform, pdist

# import statsmodels.api as sm
# #import statsmodels.formula.api as smf

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

import ukcensusapi.Nomisweb as Nomisweb
import ukcensusapi.NRScotland as NRScotland
import ukcensusapi.NISRA as NISRA

from simim.utils import get_shapefile

# TODO ukpopulation

def main():

  do_graphs = True
  do_NI = False

  cache_dir = "../microsimulation/cache"
  census_ew = Nomisweb.Nomisweb(cache_dir)
  census_sc = NRScotland.NRScotland(cache_dir)
  census_ni = NISRA.NISRA(cache_dir)

  # get OD data
  # more up-to-date here (E&W by LAD, Scotland & NI by country)
  # https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/migrationwithintheuk/datasets/internalmigrationbyoriginanddestinationlocalauthoritiessexandsingleyearofagedetailedestimatesdataset

  uk_cmlad_codes="1132462081...1132462085,1132462127,1132462128,1132462356...1132462360,1132462086...1132462089,1132462129,1132462130,1132462145...1132462150,1132462229...1132462240,1132462337...1132462351,1132462090...1132462094,1132462269...1132462275,1132462352...1132462355,1132462368...1132462372,1132462095...1132462098,1132462151...1132462158,1132462241...1132462254,1132462262...1132462268,1132462276...1132462282,1132462099...1132462101,1132462131,1132462293...1132462300,1132462319...1132462323,1132462331...1132462336,1132462361...1132462367,1132462111...1132462114,1132462134,1132462135,1132462140...1132462144,1132462178...1132462189,1132462207...1132462216,1132462255...1132462261,1132462301...1132462307,1132462373...1132462404,1132462115...1132462126,1132462136...1132462139,1132462173...1132462177,1132462196...1132462206,1132462217...1132462228,1132462283...1132462287,1132462308...1132462318,1132462324...1132462330,1132462102,1132462103,1132462132,1132462133,1132462104...1132462110,1132462159...1132462172,1132462190...1132462195,1132462288...1132462292,1132462405...1132462484"
  table = "MM01CUK_ALL"
  query_params = {
    "date": "latest",
    "usual_residence": uk_cmlad_codes,
    "address_one_year_ago": uk_cmlad_codes,
    "age": 0,
    "c_sex": 0,
    "measures": 20100,
    "select": "ADDRESS_ONE_YEAR_AGO_CODE,USUAL_RESIDENCE_CODE,OBS_VALUE"
  }
  od_2011 = census_ew.get_data(table, query_params)
  #print(od_2011.USUAL_RESIDENCE_CODE.unique())

  # TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
  lookup = pd.read_csv("../../UrbCap/data/cache/LAD_lookup.csv")
  #print(lookup.head())

  #print(od_2011.head())
  od_2011 = od_2011.merge(lookup[["CM_GEOGRAPHY_CODE", "GEOGRAPHY_CODE"]], how='left', left_on="ADDRESS_ONE_YEAR_AGO_CODE", right_on="CM_GEOGRAPHY_CODE") \
    .rename({"GEOGRAPHY_CODE": "O_GEOGRAPHY_CODE"}, axis=1).drop(["CM_GEOGRAPHY_CODE"], axis=1)
  od_2011 = od_2011.merge(lookup[["CM_GEOGRAPHY_CODE", "GEOGRAPHY_CODE"]], how='left', left_on="USUAL_RESIDENCE_CODE", right_on="CM_GEOGRAPHY_CODE") \
    .rename({"GEOGRAPHY_CODE": "D_GEOGRAPHY_CODE", "OBS_VALUE": "MIGRATIONS"}, axis=1).drop(["CM_GEOGRAPHY_CODE"], axis=1)

  # ensure blanks arising from Sc/NI not being in lookup are reinstated from original data
  od_2011.loc[pd.isnull(od_2011.O_GEOGRAPHY_CODE), "O_GEOGRAPHY_CODE"] = od_2011.ADDRESS_ONE_YEAR_AGO_CODE[pd.isnull(od_2011.O_GEOGRAPHY_CODE)]
  od_2011.loc[pd.isnull(od_2011.D_GEOGRAPHY_CODE), "D_GEOGRAPHY_CODE"] = od_2011.USUAL_RESIDENCE_CODE[pd.isnull(od_2011.D_GEOGRAPHY_CODE)]
  od_2011.drop(["ADDRESS_ONE_YEAR_AGO_CODE", "USUAL_RESIDENCE_CODE"], axis=1, inplace=True)

  # assert False

  # TODO adjustments for Westminster/City or London and Cornwall/Scilly Isles
  # for now just remove City & Scilly
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E09000001") & (od_2011.D_GEOGRAPHY_CODE != "E09000001")]
  od_2011 = od_2011[(od_2011.O_GEOGRAPHY_CODE != "E06000053") & (od_2011.D_GEOGRAPHY_CODE != "E06000053")]

  # people - use ukpopulation
  query_params = {
    "date": "latest",
    "RURAL_URBAN": "0",
    "CELL": "0",
    "MEASURES": "20100",
    "geography": "1946157057...1946157404",
    "select": "GEOGRAPHY_CODE,OBS_VALUE"
  }
  p_2011 = census_ew.get_data("KS102EW", query_params)
  
  p_2011sc = census_sc.get_data("KS102SC", "S92000003", "LAD", category_filters={"KS102SC_0_CODE": 0}).drop("KS102SC_0_CODE", axis=1)
  # print(p_2011sc.head())
  # print(len(p_2011sc))
  p_2011 = p_2011.append(p_2011sc)

  #print(census_ni.get_metadata("KS102NI", "LAD"))
  p_2011ni = census_ni.get_data("KS102NI", "N92000002", "LAD", category_filters={"KS102NI_0_CODE": 16}).drop("KS102NI_0_CODE", axis=1)
  #print(p_2011ni.head())
  p_2011 = p_2011.append(p_2011ni).rename({"OBS_VALUE": "PEOPLE"}, axis=1)
  #print(len(p_2011))

  # households
  # get total household counts per LAD

  query_params = {
    "date": "latest",
    "RURAL_URBAN": "0",
    "CELL": "0",
    "MEASURES": "20100",
    "geography": "1946157057...1946157404",
    "select": "GEOGRAPHY_CODE,OBS_VALUE"
  }
  hh_2011 = census_ew.get_data("KS105EW", query_params)
  # get Scotland
  hh_2011sc = census_sc.get_data("KS105SC", "S92000003", "LAD", category_filters={"KS105SC_0_CODE": 0}).drop("KS105SC_0_CODE", axis=1)
  # print(hh_2011sc)
  # print(len(hh_2011sc))
  hh_2011 = hh_2011.append(hh_2011sc)
  #print(len(hh_2011))

  hh_2011ni = census_ni.get_data("KS105NI", "N92000002", "LAD", category_filters={"KS105NI_0_CODE": 0}).drop("KS105NI_0_CODE", axis=1)
  # print(hh_2011ni)
  # print(len(hh_2011ni))

  hh_2011 = hh_2011.append(hh_2011ni).rename({"OBS_VALUE": "HOUSEHOLDS"}, axis=1)
  #print(len(hh_2011))

  # get distances (url is GB ultra generalised clipped LAD boundaries/centroids)
  url = "https://opendata.arcgis.com/datasets/686603e943f948acaa13fb5d2b0f1275_4.zip?outSR=%7B%22wkid%22%3A27700%2C%22latestWkid%22%3A27700%7D"
  gdf = get_shapefile(url, cache_dir)

  dists = pd.DataFrame(squareform(pdist(pd.DataFrame({"e": gdf.bng_e, "n": gdf.bng_n}))), columns=gdf.lad16cd.unique(), index=gdf.lad16cd.unique())
  # turn matrix into table
  dists = dists.stack().reset_index().rename({"level_0": "orig", "level_1": "dest", 0: "DISTANCE"}, axis=1)
  # convert to km 
  dists.DISTANCE = dists.DISTANCE / 1000.0
  #print(dists.head())

  # merge with OD
  od_2011 = od_2011.merge(dists, how="left", left_on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"], right_on=["orig", "dest"]).drop(["orig", "dest"], axis=1)

  # Merge population *at origin*
  od_2011 = od_2011.merge(p_2011, how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
  # Merge households *at destination*
  od_2011 = od_2011.merge(hh_2011, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE").drop("GEOGRAPHY_CODE", axis=1)
  print(od_2011.head())

  odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values
  #print(odmatrix.shape)

  # remove O=D rows
  od_2011 = od_2011[od_2011.O_GEOGRAPHY_CODE != od_2011.D_GEOGRAPHY_CODE]
  # set epsilon dist for O=D rows
  #od_2011.loc[od_2011.O_GEOGRAPHY_CODE == od_2011.D_GEOGRAPHY_CODE, "DISTANCE"] = 1e-0

  if not do_NI:
    ni = ['95TT', '95XX', '95OO', '95GG', '95DD', '95QQ', '95ZZ', '95VV', '95YY', '95CC',
          '95II', '95NN', '95AA', '95RR', '95MM', '95LL', '95FF', '95BB', '95SS', '95HH',
          '95EE', '95PP', '95UU', '95WW', '95KK', '95JJ']
    od_2011 = od_2011[(~od_2011.O_GEOGRAPHY_CODE.isin(ni)) & (~od_2011.D_GEOGRAPHY_CODE.isin(ni))]
    odmatrix = od_2011[["MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].set_index(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]).unstack().values

  #od_2011.to_csv("od2011.csv", index=False)


  # pysal impl
  model = "pow"
  print("model: " + model)
  gravity = Gravity(od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model)
  #print(gravity.params)
  # TODO this formula is wrong?
  k = gravity.params[0]
  mu = gravity.params[1]
  alpha = gravity.params[2]
  beta = gravity.params[3]
  if model == "pow":
    est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values
  else:
    est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * np.exp(od_2011.DISTANCE * beta)).values

  print("Unconstrained Poisson Fitted R2 = %f" % gravity.pseudoR2)
  print("Unconstrained Poisson Fitted RMSE = %f" % gravity.SRMSE)
  print(np.mean(est_unc - gravity.yhat))
  print(np.sqrt(np.mean((est_unc - gravity.yhat)**2)))

  #perturb
  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] = od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
  pert_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)

  # can only affect rows with the perturbed destination
  print(np.count_nonzero(pert_unc - est_unc)/len(est_unc)) # =1/378

  # # re-fit model
  # gravity_bumped = Gravity(od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model)
  # print(gravity.params)
  # print(gravity_bumped.params)
  # k = gravity_bumped.params[0]
  # mu = gravity_bumped.params[1]
  # alpha = gravity_bumped.params[2]
  # beta = gravity_bumped.params[3]
  # bump_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # print("Bumped Unconstrained Poisson Fitted R2 = %f" % gravity_bumped.pseudoR2)
  # print("Bumped Unconstrained Poisson Fitted RMSE = %f" % gravity_bumped.SRMSE)

  # print(np.count_nonzero(bump_unc - est_unc)/len(est_unc))

  # Unconstrained Poisson Fitted R2 = 0.575711
  # Unconstrained Poisson Fitted RMSE = 64.298780

  # alpha = np.append(np.array(0.0), attr.params[2:-1])
  # beta = attr.params[-1]
  # #T_ij = exp(k + mu ln(V_i) + alpha_j + beta * ln?(D_ij))
  # # est_attr = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # print(len(alpha), len(od_2011.D_GEOGRAPHY_CODE.unique()))

  # T0 = np.exp(k + mu * np.log(od_2011.PEOPLE.values[0]) + alpha[0] + np.log(od_2011.DISTANCE.values[0]) * beta)
  # print(T0, attr.yhat[0])
  # #print(attr.yhat)

  # Attraction constrained model
  model = "pow"
  attr = Attraction(od_2011.MIGRATIONS.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.PEOPLE.values, od_2011.DISTANCE.values, model)
  # k = attr.params[0]
  # mu = attr.params[1]

  print("Attr-constrained Poisson Fitted R2 = %f" % attr.pseudoR2)
  print("Attr-constrained Poisson Fitted RMSE = %f" % attr.SRMSE)

  doubly = Doubly(od_2011.MIGRATIONS.values, od_2011.O_GEOGRAPHY_CODE.values, od_2011.D_GEOGRAPHY_CODE.values, od_2011.DISTANCE.values, 'exp')
  print("Doubly-constrained Poisson Fitted R2 = %f" % doubly.pseudoR2)
  print("Doubly-constrained Poisson Fitted RMSE = %f" % doubly.SRMSE)

  # visualise
  if do_graphs:
    fig, [[ax1, ax2], [ax3, ax4]] = plt.subplots(nrows=2, ncols=2, figsize=(10, 10), sharex=False, sharey=False)
    #fig, [ax1, ax2] = plt.subplots(nrows=1, ncols=2, figsize=(16, 10), sharex=False, sharey=False)

    #fig.suptitle("UK LAD SIMs using population as emitter, households as attractor")
    ax1.set_title("OD matrix (displaced log scale)")
    ax1.imshow(np.log(odmatrix+1), cmap=plt.get_cmap('Greens'))
    #ax2.imshow(np.log(1+gravity.yhat), cmap=plt.get_cmap('Greens'))
    #ax2.imshow(gravity.yhat-odmatrix, cmap=plt.get_cmap('Greens'))
    ax1.xaxis.set_visible(False)
    ax1.yaxis.set_visible(False)

    ax2.set_title("Unconstrained fit: R^2=%.2f" % gravity.pseudoR2)
    ax2.plot(od_2011.MIGRATIONS, gravity.yhat, "b.")

    ax3.set_title("Attraction constrained fit: R^2=%.2f" % attr.pseudoR2)
    ax3.plot(od_2011.MIGRATIONS, attr.yhat, "k.")

    ax4.set_title("Doubly constrained fit: R^2=%.2f" % doubly.pseudoR2)
    ax4.plot(od_2011.MIGRATIONS, doubly.yhat, "r.")

    #ax3.set_title("Migration vs origin population")
    #ax3.plot(od_2011.PEOPLE, od_2011.MIGRATIONS, "k.")

    # ax4.set_title("Migration vs destination households")
    # ax4.plot(od_2011.HOUSEHOLDS, od_2011.MIGRATIONS, "r.")
    plt.tight_layout()
    plt.show()
    #fig.savefig("doc/img/sim_basic.png", transparent=True)

if __name__ == "__main__":
  main()