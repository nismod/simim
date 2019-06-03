#!/usr/bin/env python3

""" run script for Spatial Interaction Model of Internal Migration """

import os
import time
import numpy as np
from simim import simim
import simim.visuals as visuals
from simim.utils import od_matrix, get_config

def main(params):

  """ Run it """
  try:
    # print some info...
    if not os.path.isdir(params["output_dir"]):
      print("Creating output directory %s" % params["output_dir"])
      os.mkdir(params["output_dir"])

    # start timing
    start_time = time.time()

    # TODO reorganise the data returned 
    model, data, odmatrix = simim.simim(params)

    print("done. Exec time(s): ", time.time() - start_time)

  except RuntimeError as error: 
    print("RUN FAILED: ", error)
    return

  data.write_output()

  # visualise
  year = params.get("end_year", data.snpp.max_year("en"))
  if params["graphics"]:
    # fig.suptitle("UK LAD SIMs using population as emitter, households as attractor")
    v = visuals.Visual(2,3)

    v.scatter((0,0), model.dataset.MIGRATIONS, model.impl.yhat, "b.", markersize=3, 
      title="%d %s migration model fit: R^2=%.2f" % (year, params["model_type"], model.impl.pseudoR2))
    v.line((0,0), [0,max(model.dataset.MIGRATIONS)], [0,max(model.dataset.MIGRATIONS)], "k", xlabel="Observed", ylabel="Model", linewidth=0.25)

    # N.Herts = "E07000099"
    # Cambridge "E07000008"
    lad = "E07000178" # Oxford
    c = data.custom_snpp_variant[data.custom_snpp_variant.GEOGRAPHY_CODE == lad]
    v.line((0,1), c.PROJECTED_YEAR_NAME, c.PEOPLE_SNPP, "k", label="baseline", xlabel="Year", ylabel="Population", title="Impact of scenario on population (%s)" % lad)
    v.line((0,1), c.PROJECTED_YEAR_NAME, c.PEOPLE, "r", label="scenario")
    v.panel((0,1)).legend() #("b","r"), ("base", "scenario"))

    delta = data.custom_snpp_variant[data.custom_snpp_variant.PROJECTED_YEAR_NAME == max(data.custom_snpp_variant.PROJECTED_YEAR_NAME.unique())]
    gdf = data.get_shapefile().merge(delta, left_on="lad16cd", right_on="GEOGRAPHY_CODE")
    # net emigration in blue
    net_out = gdf[gdf.net_delta < 0.0]
    v.polygons((0,2), net_out, title="%s migration model implied impact on population" % params["model_type"], xlim=[120000, 670000], ylim=[0, 550000], 
      values=-net_out.net_delta, clim=(0, np.max(-net_out.net_delta)), cmap="Blues", edgecolor="darkgrey", linewidth=0.25)
    # net immigration in red
    net_in = gdf[gdf.net_delta >= 0.0] 
    v.polygons((0,2), net_in, xlim=[120000, 670000], ylim=[0, 550000], 
      values=net_in.net_delta, clim=(0, np.max(net_in.net_delta)), cmap="Reds", edgecolor="darkgrey", linewidth=0.25)

    odmatrix = od_matrix(model.dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")
    v.matrix((1,0), np.log(odmatrix+1), cmap="Greens", xlabel="Destination", ylabel="Origin", title="Actual OD matrix (displaced log scale)")
    model_odmatrix = od_matrix(model.dataset, "MODEL_MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")
    v.matrix((1,1), np.log(model_odmatrix+1), cmap="Greys", xlabel="Destination", ylabel="Origin", title="%s model OD matrix (displaced log scale)" % params["model_type"])
    # construct new OD matrix
    # TODO CHANGED_MIGRATIONS is zero in post-scenario years
    changed_odmatrix = od_matrix(model.dataset, "CHANGED_MIGRATIONS", "O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE")
    delta_odmatrix = changed_odmatrix - model_odmatrix
    # we get away with log here as no values are -ve
    v.matrix((1,2), np.log(1+delta_odmatrix), cmap="Oranges", xlabel="Destination", ylabel="Origin", title="%s model perturbed OD matrix delta" % params["model_type"])
    #absmax = max(np.max(delta_od),-np.min(delta_od))
    #v.matrix((1,2), delta_od, 'RdBu', title="Gravity model perturbed OD matrix delta", clim=(-absmax/50,absmax/50))

    v.show()
    #v.to_png("doc/img/sim_basic.png")

if __name__ == "__main__":

  params = get_config()
  main(params)

