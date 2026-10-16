"""The multi-pen trend window (Phase 6): a separate top-level window over the engine historian.

`series` reads the historian's answer for display and holds V1's tag-to-path registry; `plot` and
`table` draw what `window` hands them. The window keeps no samples: it asks the historian for its
whole visible window and repaints the answer.
"""

from ureasim.hmi.trend.plot import TAG_MIME, TrendPlot
from ureasim.hmi.trend.series import PenSource, trend_sources
from ureasim.hmi.trend.table import PenTable, RowView
from ureasim.hmi.trend.window import TrendWindow

__all__ = ["TrendWindow", "TrendPlot", "PenTable", "RowView", "PenSource", "trend_sources",
           "TAG_MIME"]
