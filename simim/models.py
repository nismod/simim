""" models.py """

import numpy as np

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Production
from pysal.contrib.spint.gravity import Doubly

_valid_types = ["gravity", "production", "attraction", "doubly"]
_valid_subtypes = ["pow", "exp"]

def validate(model_type, model_subtype):
  if not model_type in _valid_types:
    raise ValueError("invalid model type % (must be one of %s)" % (model_subtype, str(_valid_types)))
  if not model_subtype in _valid_subtypes:
    raise ValueError("invalid model subtype % (must be one of %s)" % (model_subtype, str(_valid_subtypes)))

  # TODO perturb
  #  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] = od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
  #  pert_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # can only affect rows with the perturbed destination
  # print(np.count_nonzero(pert_unc - est_unc)/len(est_unc)) # =1/378
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


class Model:
  def __init__(self, model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
    self.model_type = model_type
    self.model_subtype = model_subtype
    validate(self.model_type, self.model_subtype)

    # take a copy of the input dataset
    self.dataset = dataset.copy()

    self.y_col = y_col
    self.xo_cols = xo_cols
    self.xd_cols = xd_cols
    self.cost_col = cost_col

    # slightly complicated to compute indices for mu and alpha from params
    self.num_emit = 1 if np.isscalar(self.xo_cols) else len(self.xo_cols)
    self.num_attr = 1 if np.isscalar(self.xd_cols) else len(self.xd_cols)

    if self.model_type == "gravity":
      self.impl = Gravity(self.dataset[self.y_col].values, 
                          self.dataset[self.xo_cols].values, 
                          self.dataset[self.xd_cols].values, 
                          self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "production":
      self.impl = Production(self.dataset[self.y_col].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "attraction":
      self.impl = Attraction(self.dataset[self.y_col].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    else: #model_type == "doubly":
      self.impl = Doubly(self.dataset[self.y_col].values, 
                         self.dataset[self.xo_cols].values, 
                         self.dataset[self.xd_cols].values, 
                         self.dataset[self.cost_col].values, self.model_subtype)

    # append the model-fitted flows to the dataframe, prefixed with "MODEL_"
    self.dataset["MODEL_"+self.y_col] = self.impl.yhat

  # TODO generalise...
  def k(self):
    return self.impl.params[0]

  def mu(self, offset=0):
    # TODO multiple emit/attr for prod/attr
    if self.model_type == "production":
      return self.impl.params[1:-2]
    elif self.model_type == "attraction":
      return self.impl.params[-2]
    return self.impl.params[1+offset]

  def alpha(self, offset=0):
    # TODO multiple emit/attr for prod/attr
    if self.model_type == "production":
      return self.impl.params[-2]
    elif self.model_type == "attraction":
      return self.impl.params[1:-2]
    print("alpha:", offset, self.num_attr, -1-self.num_attr+offset)
    return self.impl.params[-1-self.num_attr+offset]

  def beta(self):
    return self.impl.params[-1]

  def __call__(self, xo=None, xd=None):
    if self.model_type == "gravity":
      assert xo is not None
      assert xd is not None
      if isinstance(xd, list):
        assert len(xd) == self.num_attr # doesnt work?
        xd_alpha = xd[0] ** self.alpha(0)
        for i in range(1,self.num_attr):
          print(i)
          xd_alpha = xd_alpha * xd[i] ** self.alpha(i)
      else:
        assert 1 == self.num_attr
        xd_alpha = xd ** self.alpha()

      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo ** self.mu() * xd_alpha * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo ** self.mu() * xd_alpha * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    elif self.model_type == "production":
      #assert xo is None
      assert xd is not None
      #mu = np.repeat(self.mu(), int(len(self.dataset)/len(self.mu())))
      mu = np.append(0, self.mu())
      mu = np.tile(mu, int(len(self.dataset)/len(mu)))
      # NB ordering is not guaranteed
      self.dataset["mu"] = np.exp(mu)
      #mu = np.repeat(0, len(self.dataset))
      assert len(mu) == len(self.dataset)
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * np.exp(mu) * xd ** self.alpha() * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * np.exp(mu) * xd ** self.alpha() * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    elif self.model_type == "attraction":
      assert xo is not None
      #assert xd is None
      alpha = np.append(0,self.alpha())
      alpha = np.repeat(alpha, int(len(self.dataset)/len(alpha)))
      # NB ordering is not guaranteed
      self.dataset["alpha"] =np.exp(alpha)
      #alpha = np.tile(self.alpha(), int(len(self.dataset)/len(self.alpha())))
      assert len(alpha) == len(self.dataset)
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo ** self.mu() * np.exp(alpha) * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo ** self.mu() * np.exp(alpha) * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    else:
      raise NotImplementedError("TODO...")

