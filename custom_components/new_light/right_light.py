from homeassistant.helpers import entity
from homeassistant.core import HomeAssistant
import logging


class RightLight:
    """RightLight object to control a single light or light group"""

    trip_points = {}

    def __init__(self, ent: entity, hass: HomeAssistant) -> None:
        self._entity = ent
        self._hass = hass

        self._logger = logging.getLogger(f"RightLight({self._entity})")

        cd = self._hass.config.as_dict()
        self._latitude = cd["latitude"]
        self._longitude = cd["longitude"]

        self._logger.error(
            f"Initialized.  Lat/Long: {self._latitude}, {self._longitude}"
        )
