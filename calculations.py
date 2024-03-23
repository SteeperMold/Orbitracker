from pyorbital.orbital import Orbital
import datetime as dt
import math
from dataclasses import dataclass, field

SATELLITES = ['METEOR-M2 2', 'METEOR-M2 3', 'NOAA 18', 'NOAA 19', 'METOP-B', 'METOP-C']


@dataclass
class OrbCalculator:
    """
    Класс, содержащий функционал для расчета траекторий спутников
    """

    lat: float
    lon: float
    alt: float
    min_elevation: float
    min_apogee: float
    start_time: dt.datetime
    duration: int
    orb: Orbital = field(init=False, default=None)

    def get_passes(self):
        """
        Возвращает расписание всех пролетающих спутников в указзаном месте в указанное время
        :returns: [[satellite_name, start_time, end_time, apogee, does_overlap], ...]
        :rtype: list[list[str, str, str, float, bool]]
        """

        all_passes = []

        for satellite in SATELLITES:
            self.orb = Orbital(satellite, 'tle.txt')
            passes = self.orb.get_next_passes(self.start_time, self.duration, self.lon, self.lat, self.alt)

            # Убираем пролеты с апогеем ниже указанного
            passes = filter(self.sort_by_min_apogee, passes)

            # Убираем из пролета части, где элевация меньше чем min_elevation
            passes = map(self.map_by_min_elevation, passes)

            # Добавляем к информации о пролете название спутника и
            # пересекается ли его время пролета со временем пролета следующего спутника
            for i in passes:
                all_passes.append([satellite, *i, False])

        # Сортируем пролеты по времени начала
        all_passes.sort(key=lambda data: data[1])

        # Проверяем, пересекается ли время пролета предыдущего спутника со следующим
        for i in range(len(all_passes) - 1):
            current_end = all_passes[i][2]
            next_start = all_passes[i + 1][1]

            if next_start <= current_end:
                # Обрезаем начало следующего пролета
                all_passes[i + 1][1] = current_end + dt.timedelta(seconds=1)
                # Указываем, что пролеты пересекаются
                all_passes[i][4] = True
                all_passes[i + 1][4] = True

        # Переводим все данные в более удобный для чтения формат
        all_passes = list(map(self.prepare_data, all_passes))

        return all_passes

    def sort_by_min_apogee(self, datetimes):
        start, end, max_elevation = datetimes
        azimuth, elevation = self.orb.get_observer_look(max_elevation, self.lon, self.lat, self.alt)
        return elevation >= self.min_apogee

    def map_by_min_elevation(self, datetimes):
        start, end, max_elevation = datetimes
        mapped_start, mapped_end = start, end

        for shift in range((max_elevation - start).seconds):
            elevation = self.orb.get_observer_look(start + dt.timedelta(seconds=shift), self.lon, self.lat, self.alt)[1]

            if math.floor(elevation) >= self.min_elevation:
                mapped_start = start + dt.timedelta(seconds=shift)
                break

        for shift in range((end - max_elevation).seconds):
            elevation = self.orb.get_observer_look(end - dt.timedelta(seconds=shift), self.lon, self.lat, self.alt)[1]

            if math.floor(elevation) >= self.min_elevation:
                mapped_end = end - dt.timedelta(seconds=shift)
                break

        return mapped_start, mapped_end, max_elevation

    def prepare_data(self, data):
        name, start_time, end_time, max_elevation_time, is_highlighted = data
        start_time = start_time.strftime('%Y.%m.%d %H:%M:%S')
        end_time = end_time.strftime('%Y.%m.%d %H:%M:%S')
        apogee = Orbital(name, 'tle.txt').get_observer_look(max_elevation_time, self.lon, self.lat, self.alt)[1]
        return name, start_time, end_time, round(apogee, 2), is_highlighted
