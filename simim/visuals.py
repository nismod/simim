""" visuals.py """

import numpy as np
from geopandas.plotting import plot_polygon_collection
import matplotlib.pyplot as plt

# https://matplotlib.org/examples/color/colormaps_reference.html

class Visual:
  def __init__(self, rows, cols, panel_x=5, panel_y=5):
    self.rows = rows
    self.cols = cols
    self.fig, self.axes = plt.subplots(nrows=rows, ncols=cols, figsize=(cols*panel_x, rows*panel_y), sharex=False, sharey=False)

  def panel(self, index):
    # deal with non-array case
    if self.rows == 1 and self.cols == 1:
      return self.axes
    elif self.rows == 1:
      return self.axes[index[1]]
    elif self.cols == 1:
      return self.axes[index[0]]
    else:
      return self.axes[index]

  # TODO legend not working
  def line(self, panel, x, y, marker, title=None, xlabel=None, ylabel=None, **kwargs):
    ax = self.panel(panel)
    if xlabel:
      ax.set_xlabel(xlabel)
    if ylabel:
      ax.set_ylabel(ylabel)
    if title:
      ax.set_title(title)
    # if "label" in kwargs:
    #   ax.legend()
    ax.plot(x, y, marker, **kwargs)

  def stacked_bar(self, panel, alldata, category_name, xaxis_name, yaxis_name, title=None, xlabel=None, ylabel=None, **kwargs):

    categories = alldata[category_name].unique()
    bottom = np.zeros(len(alldata[xaxis_name].unique()))

    ax = self.panel(panel)
    series = []
    for cat in categories:
      x = alldata[alldata[category_name] == cat][xaxis_name].values
      y = alldata[alldata[category_name] == cat][yaxis_name].values
      series.append(ax.bar(x, y, bottom=bottom))
      bottom += y

    ax.set_xlabel(xlabel if xlabel is not None else xaxis_name)
    ax.set_ylabel(ylabel if ylabel is not None else yaxis_name)
    ax.legend([p[0] for p in series], categories)
    #plt.show()


  def scatter(self, panel, x, y, marker, title=None, **kwargs):
    ax = self.panel(panel)
    if title:
      ax.set_title(title)
    ax.plot(x, y, marker, **kwargs)

  def matrix(self, panel, matrix, title=None, xlabel=None, ylabel=None, **kwargs):
    ax = self.panel(panel)
    if xlabel:
      ax.set_xlabel(xlabel)
    if ylabel:
      ax.set_ylabel(ylabel)
    if title:
      ax.set_title(title)
    ax.imshow(matrix, **kwargs)
    ax.set_xticks([])
    ax.set_yticks([])

  def polygons(self, panel, gdf, title=None, xlim=None, ylim=None, **kwargs):
    ax = self.panel(panel)
    ax.set_xticks([])
    ax.set_yticks([])
    if title:
      ax.set_title(title)
    if xlim:
      ax.set_xlim(xlim)
    if ylim:
      ax.set_ylim(ylim)

    plot_polygon_collection(ax, gdf['geometry'], **kwargs)

  def show(self):
    plt.tight_layout()
    plt.show()

  def to_png(self, filename):
    self.fig.savefig(filename, transparent=True)

