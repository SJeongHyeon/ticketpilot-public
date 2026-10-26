"""Keep tkinter discoverable when its Tcl/Tk probe cannot initialize."""


def pre_find_module_path(hook_api) -> None:
    """Use Python's standard-library tkinter package search path unchanged."""
