from .panels import register as register_panels
from .ui import register as register_ui

def register():
    register_panels()
    register_ui()

def unregister():
    register_ui()
    register_panels()