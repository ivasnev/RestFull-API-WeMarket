from .imports import ImportsView
from .delete import DeleteView
from .nodes import NodesView
from .sales import SalesView

HANDLERS = (
    DeleteView,
    ImportsView,
    NodesView,
    SalesView
)
