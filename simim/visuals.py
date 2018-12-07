""" visuals.py """

from geopandas.plotting import plot_polygon_collection
import matplotlib.pyplot as plt

# https://matplotlib.org/examples/color/colormaps_reference.html

class Visual:
  def __init__(self, rows, cols):
    self.rows = rows
    self.cols = cols
    self.fig, self.axes = plt.subplots(nrows=rows, ncols=cols, figsize=(cols*5, rows*5), sharex=False, sharey=False)

  def panel(self, index):
    return self.axes[index]

  def scatter(self, panel, x, y, marker="k.", title=None, **kwargs):
    ax = self.axes[panel]
    if title:
      ax.set_title(title)
    ax.plot(x, y, marker, **kwargs)

  def matrix(self, panel, matrix, cmap="Greys", title=None, **kwargs):
    ax = self.axes[panel]
    if title:
      ax.set_title(title)
    ax.imshow(matrix, cmap=cmap, **kwargs)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

  def polygons(self, panel, gdf, xlim, ylim, edge_colour, fill_colour):
    ax = self.axes[panel]
    ax.axis("off")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    plot_polygon_collection(ax, gdf['geometry'], edgecolor="white", facecolor=fill_colour, linewidth=0)
    #gdf.plot(alpha=0.5, edgecolor='k', color=gdf.fill_colour, ax=ax)

  def show(self):
    plt.tight_layout()
    plt.show()

  def to_png(self, filename):
    self.fig.savefig(filename, transparent=True)

