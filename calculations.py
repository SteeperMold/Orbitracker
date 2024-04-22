from pyorbital.orbital import Orbital
import datetime as dt
import math

SATELLITES = ['METEOR-M2 2', 'METEOR-M2 3', 'NOAA 18', 'NOAA 19', 'METOP-B', 'METOP-C']


class OrbCalculator:
    """
    Класс, содержащий функционал для расчета траекторий спутников
    """

    @staticmethod
    def get_passes(lat: float, lon: float, alt: float, min_elevation: float, min_apogee: float,
                   start_time: dt.datetime, duration: int):
        """
        Возвращает расписание всех пролетающих спутников в указзаном месте в указанное время
        :returns: [[satellite_name, start_time, end_time, apogee, does_overlap], ...]
        :rtype: list[list[str, str, str, float, bool]]
        """

        def sort_by_min_apogee(datetimes):
            start, end, max_elevation = datetimes
            azimuth, elevation = orb.get_observer_look(max_elevation, lon, lat, alt)
            return elevation >= min_apogee

        def map_by_min_elevation(datetimes):
            start, end, max_elevation = datetimes
            mapped_start, mapped_end = start, end

            for shift in range((max_elevation - start).seconds):
                elevation = orb.get_observer_look(start + dt.timedelta(seconds=shift), lon, lat, alt)[1]

                if math.floor(elevation) >= min_elevation:
                    mapped_start = start + dt.timedelta(seconds=shift)
                    break

            for shift in range((end - max_elevation).seconds):
                elevation = orb.get_observer_look(end - dt.timedelta(seconds=shift), lon, lat, alt)[1]

                if math.floor(elevation) >= min_elevation:
                    mapped_end = end - dt.timedelta(seconds=shift)
                    break

            return mapped_start, mapped_end, max_elevation

        def prepare_data(data):
            name, start_time, end_time, max_elevation_time = data
            start_time = start_time.strftime('%Y.%m.%d %H:%M:%S')
            end_time = end_time.strftime('%Y.%m.%d %H:%M:%S')
            apogee = Orbital(name, 'tle.txt').get_observer_look(max_elevation_time, lon, lat, alt)[1]
            return name, start_time, end_time, round(apogee, 2)

        all_passes = []

        for satellite in SATELLITES:
            orb = Orbital(satellite, 'tle.txt')
            passes = orb.get_next_passes(start_time, duration, lon, lat, alt)

            # Убираем пролеты с апогеем ниже указанного
            passes = filter(sort_by_min_apogee, passes)

            # Убираем из пролета части, где элевация меньше чем min_elevation
            passes = map(map_by_min_elevation, passes)

            # Добавляем к информации о пролете название спутника
            for i in passes:
                all_passes.append([satellite, *i])

        # Сортируем пролеты по времени начала
        all_passes.sort(key=lambda data: data[1])

        # Переводим все данные в более удобный для чтения формат
        all_passes = list(map(prepare_data, all_passes))

        return all_passes

