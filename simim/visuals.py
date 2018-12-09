""" visuals.py """

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
    return self.axes[index]

  def scatter(self, panel, x, y, marker="k.", title=None, **kwargs):
    ax = self.panel(panel)
    if title:
      ax.set_title(title)
    ax.plot(x, y, marker, **kwargs)

  def matrix(self, panel, matrix, cmap="Greys", title=None, **kwargs):
    ax = self.panel(panel)
    if title:
      ax.set_title(title)
    ax.imshow(matrix, cmap=cmap, **kwargs)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

  def polygons(self, panel, gdf, xlim, ylim, **kwargs):
    #ax = self.axes[panel]
    ax = self.panel(panel)
    ax.axis("off")
    if xlim:
      ax.set_xlim(xlim)
    if ylim:
      ax.set_ylim(ylim)

    plot_polygon_collection(ax, gdf['geometry'], linewidth=0.25, **kwargs)

  def polygons2(self, panel, gdf, xlim, ylim, values, **kwargs):
    #ax = self.axes[panel]
    ax = self.panel(panel)
    ax.axis("off")
    if xlim:
      ax.set_xlim(xlim)
    if ylim:
      ax.set_ylim(ylim)

    plot_polygon_collection(ax, gdf['geometry'], values=values, **kwargs)

  def show(self):
    plt.tight_layout()
    plt.show()

  def to_png(self, filename):
    self.fig.savefig(filename, transparent=True)

