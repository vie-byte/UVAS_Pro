from .generation import register as register_generation
from .editing import register as register_editing
from .management import register as register_management

def register():
    register_generation()
    register_editing()
    register_management()

def unregister():
    register_management()
    register_editing()
    register_generation()