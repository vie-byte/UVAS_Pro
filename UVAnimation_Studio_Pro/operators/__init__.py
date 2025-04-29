from .generate import register as register_generate
from .tile import register as register_tile
from .management import register as register_management
from .uv_anim import register as register_uv_anim

def register():
    register_generate()
    register_tile()
    register_management()
    register_uv_anim()

def unregister():
    register_uv_anim()
    register_management()
    register_tile()
    register_generate()