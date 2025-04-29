bl_info = {
    "name": "UVAnimation Studio Pro",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (4, 4, 0),
    "location": "Image Editor > Sidebar > UVAS Studio",
    "description": "Advanced UV animation and tile manipulation tools",
    "category": "Image",
}

import bpy
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from . import operators
from . import ui
from . import properties
from . import node

def register():
    try:
        logger.debug("Registering properties")
        properties.register()
        logger.debug("Registering operators")
        operators.register()
        logger.debug("Registering ui")
        ui.register()
        logger.debug("Registering node")
        node.register()
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise

def unregister():
    try:
        logger.debug("Unregistering node")
        node.unregister()
        logger.debug("Unregistering ui")
        ui.unregister()
        logger.debug("Unregistering operators")
        operators.unregister()
        logger.debug("Unregistering properties")
        properties.unregister()
    except Exception as e:
        logger.error(f"Unregistration failed: {e}")
        raise

if __name__ == "__main__":
    register()