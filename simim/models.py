""" models.py """

import numpy as np

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Production
from pysal.contrib.spint.gravity import Doubly

_valid_types = ["gravity", "production", "attraction", "doubly"]
_valid_subtypes = ["pow", "exp"]

def validate(model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
  if not model_type in _valid_types:
    raise ValueError("invalid model type % (must be one of %s)" % (model_subtype, str(_valid_types)))
  if not model_subtype in _valid_subtypes:
    raise ValueError("invalid model subtype % (must be one of %s)" % (model_subtype, str(_valid_subtypes)))
  if not "O_GEOGRAPHY_CODE" in dataset.columns.values:
    raise ValueError("dataset must contain an O_GEOGRAPHY_CODE column for origin identifiers")
  if not "D_GEOGRAPHY_CODE" in dataset.columns.values:
    raise ValueError("dataset must contain an D_GEOGRAPHY_CODE column for destination identifiers")
  if not y_col in dataset.columns.values:
    raise ValueError("observation column specified to be %s but it's not in the dataset" % y_col)
  # TODO validate xo/xd cols...
  if not cost_col in dataset.columns.values:
    raise ValueError("cost function column specified to be %s but it's not in the dataset" % cost_col)

class Model:
  def __init__(self, model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
    self.model_type = model_type
    self.model_subtype = model_subtype
    validate(self.model_type, self.model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col)

    self.dataset = dataset.copy()
    # TODO needs more thought...
    # take a copy of the input dataset and ensure sorted by D then O
    # so that the ordering of mu, alpha is determined
    #self.dataset = dataset.sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"])
    # now we have copy, invalidate the input!!!
    #dataset = None

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
      raise NotImplemented("Doubly constrained model is too constrained")
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
    #print(self.impl.params[1+offset])
    return self.impl.params[1+offset]

  def alpha(self, offset=0):
    # TODO multiple emit/attr for prod/attr
    if self.model_type == "production":
      return self.impl.params[-2]
    elif self.model_type == "attraction":
      return self.impl.params[1:-2]
    return self.impl.params[-1-self.num_attr+offset]

  def beta(self):
    return self.impl.params[-1]

  def __calc_xo_mu(self, xo):
    if isinstance(xo, list):
      assert len(xo) == self.num_emit 
      xo_mu = xo[0] ** self.mu(0)
      for i in range(1,self.num_emit):
        xo_mu = xo_mu * xo[i] ** self.mu(i)
    else:
      assert 1 == self.num_emit
      xo_mu = xo ** self.mu()
    return xo_mu

  def __calc_xd_alpha(self, xd):
    if isinstance(xd, list):
      assert len(xd) == self.num_attr 
      xd_alpha = xd[0] ** self.alpha(0)
      for i in range(1,self.num_attr):
        xd_alpha = xd_alpha * xd[i] ** self.alpha(i)
    else:
      assert 1 == self.num_attr
      xd_alpha = xd ** self.alpha()
    return xd_alpha

  def __call__(self, xo=None, xd=None):
    if self.model_type == "gravity":
      assert xo is not None
      assert xd is not None
      xo_mu = self.__calc_xo_mu(xo)
      xd_alpha = self.__calc_xd_alpha(xd)

      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo_mu * xd_alpha * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo_mu * xd_alpha * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    elif self.model_type == "production":
      #assert xo is None
      assert xd is not None
      mu = np.append(0, self.mu())
      mu = np.tile(mu, int(len(self.dataset)/len(mu)))
      assert len(mu) == len(self.dataset)
      # NB ordering is only guaranteed if dataset is sorted by origin then destination code
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
      assert len(alpha) == len(self.dataset)
      # NB ordering is only guaranteed if dataset is sorted by origin then destination code
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo ** self.mu() * np.exp(alpha) * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo ** self.mu() * np.exp(alpha) * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    else:
      raise NotImplementedError("%s evaluation not implemented" % self.model_type)

