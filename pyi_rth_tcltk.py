"""Set Tcl/Tk library locations before TicketPilot imports tkinter."""

import os
from pathlib import Path
import sys


bundle_root = Path(sys._MEIPASS)
os.environ["TCL_LIBRARY"] = str(bundle_root / "_tcl_data")
os.environ["TK_LIBRARY"] = str(bundle_root / "_tk_data")
