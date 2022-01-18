from homeassistant.helpers import entity
from homeassistant.core import HomeAssistant
import logging, pytz
from suntime import Sun, SunTimeException
from datetime import date, timedelta
import datetime


class RightLight:
    """RightLight object to control a single light or light group"""


    def __init__(self, ent: entity, hass: HomeAssistant) -> None:
        self._entity = ent
        self._hass = hass

        self._logger = logging.getLogger(f"RightLight({self._entity})")

        self.trip_points = {}

        cd = self._hass.config.as_dict()
        self._latitude = cd["latitude"]
        self._longitude = cd["longitude"]
        self._timezone = cd["time_zone"]

        self._logger.error(
            f"Initialized.  Lat/Long: {self._latitude}, {self._longitude}"
        )

        sun = Sun(latitude, longitude)
        tz = pytz.timezone(self._timezone)

        self.sunrise = sun.get_sunrise_time(date.today()).astimezone(tz)
        self.sunset = sun.get_sunset_time(date.today()).astimezone(tz)

        self.defineTripPoints()

        self._logger.error(f"Trip Points Normal: {self.trip_points['Normal']}")

    def defineTripPoints(self):
        self.trip_points["Normal"] = []
        now = datetime.datetime.now()

        self.trip_points["Normal"].append( [now.replace(microsecond=0, second=1, minute=0, hour=0), 2500, 150] )  # Midnight morning
        self.trip_points["Normal"].append( [self.sunrise - timedelta(minutes=60), 2500, 120] )  # Sunrise - 60
        self.trip_points["Normal"].append( [self.sunrise - timedelta(minutes=30), 2700, 170] )  # Sunrise - 30
        self.trip_points["Normal"].append( [self.sunrise, 3200, 155] )  # Sunrise
        self.trip_points["Normal"].append( [self.sunrise + timedelta(minutes=30), 4700, 255] )  # Sunrise + 30
        self.trip_points["Normal"].append( [self.sunset - timedelta(minutes=90), 4200, 255] )  # Sunset - 90
        self.trip_points["Normal"].append( [self.sunset - timedelta(minutes=30), 3200, 255] )   # Sunset = 30
        self.trip_points["Normal"].append( [self.sunset, 2700, 255]) # Sunset
        self.trip_points["Normal"].append( [now.replace(microsecond=0, second=0, minute=30, hour=22), 2500, 255]) # 10:30
        self.trip_points["Normal"].append( [now.replace(microsecond=0, second=59, minute==59, hour=23), 2500, 150]) # Midnight night