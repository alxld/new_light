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

        sun = Sun(self._latitude, self._longitude)
        tz = pytz.timezone(self._timezone)

        self.sunrise = sun.get_sunrise_time(date.today()).astimezone(tz)
        self.sunset = sun.get_sunset_time(date.today()).astimezone(tz)

        self.defineTripPoints()

        #self._logger.error(f"Trip Points Normal: {self.trip_points['Normal']}")
        self._logger.error(f"Trip Points Vivid: {self.trip_points['Vivid']}")

    def defineTripPoints(self):
        self.trip_points["Normal"] = []
        now = datetime.datetime.now()
        midnight_early = now.replace(microsecond=0, second=0, minute=0, hour=0)
        midnight_late  = now.replace(microsecond=0, second=59, minute=59, hour=11)
        timestep = timedelta(minutes=2)

        self.trip_points["Normal"].append( [midnight_early, 2500, 150] )  # Midnight morning
        self.trip_points["Normal"].append( [self.sunrise - timedelta(minutes=60), 2500, 120] )  # Sunrise - 60
        self.trip_points["Normal"].append( [self.sunrise - timedelta(minutes=30), 2700, 170] )  # Sunrise - 30
        self.trip_points["Normal"].append( [self.sunrise, 3200, 155] )  # Sunrise
        self.trip_points["Normal"].append( [self.sunrise + timedelta(minutes=30), 4700, 255] )  # Sunrise + 30
        self.trip_points["Normal"].append( [self.sunset - timedelta(minutes=90), 4200, 255] )  # Sunset - 90
        self.trip_points["Normal"].append( [self.sunset - timedelta(minutes=30), 3200, 255] )   # Sunset = 30
        self.trip_points["Normal"].append( [self.sunset, 2700, 255]) # Sunset
        self.trip_points["Normal"].append( [now.replace(microsecond=0, second=0, minute=30, hour=22), 2500, 255]) # 10:30
        self.trip_points["Normal"].append( [midnight_late, 2500, 150]) # Midnight night

        vivid_trip_points = [
            [255,   0,   0],
            [202,   0, 127],
            [130,   0, 255],
            [  0,   0, 255],
            [  0,  90, 190],
            [  0, 200, 200],
            [  0, 255,   0],
            [255, 255,   0],
            [255, 127,   0]
        ]

        bright_trip_points = [
            [255, 100, 100],
            [202,  80, 127],
            [150,  70, 255],
            [ 90,  90, 255],
            [ 60, 100, 190],
            [ 70, 200, 200],
            [ 80, 255,  80],
            [255, 255,   0],
            [255, 127,  70]
        ]

        one_trip_points = [
            [  0, 104, 255],
            [255,   0, 255]
        ]

        two_trip_points = [
            [255,   0, 255],
            [  0, 104, 255]
        ]

        # Loop to create vivid trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['Vivid'] = []
        while temp < midnight_late:
            self.trip_points['Vivid'].append( [ temp, vivid_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr > len(vivid_trip_points):
                this_ptr = 0

        # Loop to create bright trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['Bright'] = []
        while temp < midnight_late:
            self.trip_points['Bright'].append( [ temp, bright_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr > len(bright_trip_points):
                this_ptr = 0

        # Loop to create 'one' trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['One'] = []
        while temp < midnight_late:
            self.trip_points['One'].append( [ temp, one_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr > len(one_trip_points):
                this_ptr = 0

        # Loop to create 'two' trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['Two'] = []
        while temp < midnight_late:
            self.trip_points['Two'].append( [ temp, two_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr > len(two_trip_points):
                this_ptr = 0