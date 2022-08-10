from .imports import ImportsView
from .delete import DeleteView
from .nodes import NodesView



HANDLERS = (
    DeleteView,
    ImportsView,
    NodesView
)
