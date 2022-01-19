from homeassistant.helpers import entity
from homeassistant.core import HomeAssistant
import logging, pytz
from suntime import Sun, SunTimeException
from datetime import date, timedelta
import datetime, asyncio

#TODO: Put upper limit on brightness + override
#TODO: Implement colors and other modes
#TODO: Transition to next trip point
#TODO: Schedule update at next trip point (hass.loop.call_later(hass, time_delta|float, HASS_JOB|CALLABLE))

class RightLight:
    """RightLight object to control a single light or light group"""


    def __init__(self, ent: entity, hass: HomeAssistant) -> None:
        self._entity = ent
        self._hass = hass

        self._logger = logging.getLogger(f"RightLight({self._entity})")

        self.trip_points = {}

        self._ct_high = 5000
        self._ct_scalar = 0.35

        cd = self._hass.config.as_dict()
        self._latitude = cd["latitude"]
        self._longitude = cd["longitude"]
        self._timezone = cd["time_zone"]
        self._timezoneobj = pytz.timezone(self._timezone)

        self._logger.error(
            f"Initialized.  Lat/Long: {self._latitude}, {self._longitude}"
        )

        sun = Sun(self._latitude, self._longitude)

        self.sunrise = sun.get_sunrise_time(date.today()).astimezone(self._timezoneobj)
        self.sunset = sun.get_sunset_time(date.today()).astimezone(self._timezoneobj)

        self.defineTripPoints()

        #self._logger.error(f"Trip Points Normal: {self.trip_points['Normal']}")
        #self._logger.error(f"Trip Points Vivid: {self.trip_points['Vivid']}")

    async def turn_on(self, brightness: int = 255, brightness_override: int = 0):
        self._brightness = brightness
        self._brightness_override = brightness_override
        now = self._timezoneobj.localize( datetime.datetime.now() )

        # Find trip points around current time
        for next in range(0, len(self.trip_points['Normal'])):
            if self.trip_points['Normal'][next][0] >= now:
                break
        prev = next - 1

        # Calculate how far through the trip point span we are now
        prev_time = self.trip_points['Normal'][prev][0]
        next_time = self.trip_points['Normal'][next][0]
        time_ratio = (now - prev_time) / (next_time - prev_time)

        self._logger.error(f"Prev/Next: {prev}, {next}, {prev_time}, {next_time}, {time_ratio}")

        # Compute br/ct for previous point
        br_max_prev = self.trip_points['Normal'][prev][2] / 255
        br_prev = br_max_prev * (self._brightness + self._brightness_override)

        ct_max_prev = self.trip_points['Normal'][prev][1]
        ct_delta_prev = (self._ct_high - ct_max_prev) * (1 - br_max_prev) * self._ct_scalar
        ct_prev = ct_max_prev - ct_delta_prev

        # Compute br/ct for next point
        br_max_next = self.trip_points['Normal'][next][2] / 255
        br_next = br_max_next * (self._brightness + self._brightness_override)

        ct_max_next = self.trip_points['Normal'][next][1]
        ct_delta_next = (self._ct_high - ct_max_next) * (1 - br_max_next) * self._ct_scalar
        ct_next = ct_max_next - ct_delta_next

        self._logger.error(f"Prev/Next: {br_prev}/{ct_prev}, {br_next}/{ct_next}")

        # Scale linearly to current time
        br = (br_next - br_prev) * time_ratio + br_prev
        ct = (ct_next - ct_prev) * time_ratio + ct_prev

        self._logger.error(f"Final: {br}/{ct}")

        self._mode = 'Normal'
        #self._hass.states.async_set( self._entity, f"rlon: {br},{ct}" )
        await self._hass.services.async_call("light", "turn_on", {"entity_id": self._entity, "brightness": br, "kelvin": ct})


    async def disable_and_turn_off(self):
        self._brightness = 0
        #self._hass.states.async_set(self._entity, "off")
        await self._hass.services.async_call("light", "turn_off", {"entity_id": self._entity})

    def disable(self):
        pass

    def defineTripPoints(self):
        self.trip_points["Normal"] = []
        now = self._timezoneobj.localize( datetime.datetime.now() )
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
            if this_ptr >= len(vivid_trip_points):
                this_ptr = 0

        # Loop to create bright trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['Bright'] = []
        while temp < midnight_late:
            self.trip_points['Bright'].append( [ temp, bright_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr >= len(bright_trip_points):
                this_ptr = 0

        # Loop to create 'one' trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['One'] = []
        while temp < midnight_late:
            self.trip_points['One'].append( [ temp, one_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr >= len(one_trip_points):
                this_ptr = 0

        # Loop to create 'two' trip points
        temp = midnight_early
        this_ptr = 0
        self.trip_points['Two'] = []
        while temp < midnight_late:
            self.trip_points['Two'].append( [ temp, two_trip_points[this_ptr] ] )

            temp = temp + timestep

            this_ptr = this_ptr + 1
            if this_ptr >= len(two_trip_points):
                this_ptr = 0