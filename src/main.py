# get metar status of the biggest airports in the US and display lights based on the status
# TODO: maybe add crosswind component limit, would require more airport information, possibly just for local airport
# TODO: figure out the best way to update data
# TODO: decide on hardware
# FIXME: handle errors
# working time so far ~3.5 hours
import logging
import json

from get_data import update_data

logging.basicConfig(level=logging.DEBUG)


class MetarData:
    """A class for holding all organizational methods regarding the METAR data obtained from 'get_data.py'"""

    FORBIDDEN_WORDS = ["AUTO", "AO2"]
    VALID_DATA_KEYS = [
        "station",
        "time",
        "wind",
        "visibility",
        "sky",
        "temp",
        "altimiter",
        "remarks",
    ]
    BAD_REMARKS = [
        "SN",
        "FZFG",
        "FC",
        "TS",
        "FZRA",
        "GR",
        "GS",
        "VA",
        "SQ",
        "TORNADO",
        "FUNNEL CLOUD",
        "WATERSPOUT",
        "LTG",
        "TSB",
    ]

    def __init__(self, data: list):
        self.metars = self.__build_metar_dict(data)
        self.status_leds = {
            station: {"color": "green", "reason": "clear"} for station in self.metars
        }
        self.limits = {
            "wind": 50,
            "gust_factor": 20,
            "visibility": 5,
            "lower_temp": 5,
            "upper_temp": 50,
            "ceiling": 3,
        }
        self.__parse_data()

    def __build_metar_dict(self, data: list):
        """Builds a dictionary of METAR data from the data list"""
        metars = {}
        for entry in data:
            entry = entry.split()
            for word in entry:
                if word in self.FORBIDDEN_WORDS:
                    entry.remove(word)
                if word == "RMK":
                    remarks = entry[entry.index(word) + 1 :]
            entry_dict = {
                "station": entry[0],
                "time": entry[1],
                "wind": entry[2],
                "visibility": entry[3],
                "sky": entry[4],
                "temp": entry[5],
                "altimiter": entry[6],
                "remarks": remarks,
            }
            metars[entry_dict["station"]] = entry_dict
        return metars

    def __parse_wind(self):
        """Parses the wind data"""
        for station in self.metars:
            wind = self.metars[station]["wind"]
            wind = wind.replace("KT", "")
            direction = "VRB" if "VRB" in wind else wind[:3]
            wind = wind.replace(direction, "")
            if "G" in wind:
                wind = wind.split("G")
                speed = wind[0]
                gust = wind[1]
            else:
                speed = wind
                gust = 0
            wind_dict = {
                "direction": int(direction),
                "speed": int(speed),
                "gust": int(gust),
            }
            self.metars[station]["wind"] = wind_dict

    def __parse_temp(self):
        """Parses the temperature data"""
        for station in self.metars:
            temp = self.metars[station]["temp"]
            temp = temp.split("/")
            dewpoint = temp[1]
            temperature = temp[0]
            dewpoint = dewpoint.replace("M", "-") if "M" in dewpoint else dewpoint
            temperature = (
                temperature.replace("M", "-") if "M" in temperature else temperature
            )
            self.metars[station]["temp"] = {
                "temp": int(temperature),
                "dewpoint": int(dewpoint),
            }

    def __parse_sky(self):
        """Parses the sky data"""
        for station in self.metars:
            sky = self.metars[station]["sky"]
            if "CLR" in sky:
                self.metars[station]["sky"] = {"sky": "CLR", "ceiling": 999}
            else:
                sky_alt = sky[-3:] if "VV" not in sky else "VV"
                sky = sky.replace(sky_alt, "")
                self.metars[station]["sky"] = {"sky": sky, "ceiling": int(sky_alt)}

    def __parse_altimiter(self):
        """Parses the altimiter data"""
        for station in self.metars:
            new = self.metars[station]["altimiter"].replace("A", "")
            self.metars[station]["altimiter"] = new

    def __set_status_leds(self):
        """Sets the status leds based on the data"""
        for station in self.metars:
            station_name = self.metars[station]["station"]
            wind = self.metars[station]["wind"]
            sky = self.metars[station]["sky"]
            vis = self.metars[station]["visibility"]
            temp = self.metars[station]["temp"]
            remarks = self.metars[station]["remarks"]

            # Check for wind restrictions
            if wind["gust"] != 0:
                if wind["gust"] - wind["speed"] >= self.limits["gust_factor"]:
                    self.set_led(station_name, "red", "gust")
                    continue

            elif wind["speed"] >= self.limits["wind"]:
                self.set_led(station_name, "red", "wind")
                continue

            elif wind["speed"] >= 35:
                self.set_led(station_name, "yellow", "wind")
                continue

            # Check for visibility restrictions
            if "/" in vis:
                self.set_led(station_name, "red", "visibility")
                continue
            if int(vis.replace("SM", "")) <= self.limits["visibility"]:
                self.set_led(station_name, "red", "visibility")
                continue
            elif int(vis.replace("SM", "")) <= 5:
                self.set_led(station_name, "yellow", "visibility")
                continue

            # Check for sky restrictions
            bad_sky = ["OVC", "BKN"]
            if sky["ceiling"] <= self.limits["ceiling"] and sky["sky"] in bad_sky:
                self.set_led(station_name, "red", "sky")
                continue
            elif sky["ceiling"] <= 5:
                self.set_led(station_name, "yellow", "sky")
                continue

            # Check for temperature restrictions
            if (
                temp["temp"] <= self.limits["lower_temp"]
                or temp["temp"] >= self.limits["upper_temp"]
            ):
                self.set_led(station_name, "red", "temp")
                continue

            # Check for dubious remarks
            for remark in remarks:
                if remark in self.BAD_REMARKS:
                    self.set_led(station_name, "red", remark)
                    continue

    def __parse_data(self):
        """Parses all data to be easily readable/workable"""
        self.__parse_wind()
        self.__parse_temp()
        self.__parse_sky()
        self.__parse_altimiter()
        self.__set_status_leds()
        # dump metar and status leds to some files, here for debugging purposes
        with open("F:/metar-board/src/debug_data/metars.json", "w") as file:
            json.dump(self.metars, file, indent=4)
        with open("F:/metar-board/src/debug_data/leds.json", "w") as file:
            json.dump(self.status_leds, file, indent=4)

    def update(self, codes: list or str):
        """Updates the metar data"""
        data = update_data("selenium", codes)
        self.metars = self.__build_metar_dict(data)
        self.__parse_data()

    def set_limit(self, limit: str, value: int):
        """Sets a personal limit in the limits dictionary"""
        if limit not in self.limits:
            raise ValueError("Invalid limit")
        else:
            self.limits[limit] = value

    def set_led(self, station: str, color: str, reason: str):
        """Sets a status led for a station, includes the reason for the color"""
        if station not in self.status_leds:
            raise ValueError("Invalid station")
        if color not in ["red", "yellow", "green"]:
            raise ValueError("Invalid color")
        self.status_leds[station] = {"color": color, "reason": reason}

    def get_data(self, station: str, data: str):
        """Request specific data from the metar dictionary"""
        if data not in self.VALID_DATA_KEYS:
            raise ValueError("Invalid data key")
        return self.metars[station][data]


if __name__ == "__main__":
    codes = [
        "KTKI",
        "KDTO",
        "KDFW",
        "KDAL",
        "KHQZ",
        "KFWS",
        "KFTW",
        "KAFW",
        "KRBD",
        "KGKY",
    ]
    data = update_data("selenium", codes)
    # data = [
    #    "KTKI 010753Z AUTO 18080KT 10SM CLR 13/11 A3003 RMK AO2 SLP170 T01330106",
    #    "KDTO 010753Z AUTO 19005KT 10SM CLR 14/10 A3002 RMK AO2 SLP160 T01390100",
    # ]
    metar = MetarData(data)
