from io import BytesIO
import datetime as dt
from flask import Flask, render_template, request, send_file
from pyorbital.orbital import Orbital
from calculations import OrbCalculator


app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/', methods=['POST'])
def get_timetable():
    try:
        lat = float(request.form.get('lat-input'))
        lon = float(request.form.get('lon-input'))
        alt = float(request.form.get('alt-input')) / 1000
        min_elevation = float(request.form.get('min-elevation-input'))
        min_apogee = float(request.form.get('min-apogee-input'))
        start_time = dt.datetime.strptime(request.form.get('start-time-input'), '%Y-%m-%dT%H:%M')
        duration = int(request.form.get('duration-input'))
    except ValueError:
        return render_template('error.html')

    orb_calc = OrbCalculator(lat, lon, alt, min_elevation, min_apogee, start_time, duration)
    all_passes = orb_calc.get_passes()

    return render_template('index.html', passes=all_passes, lon=lon, lat=lat, alt=alt)


@app.route('/download_trajectory', methods=['POST'])
def download_trajectory():
    data = request.get_json()
    satellite = data.get('satellite')
    start_time = dt.datetime.strptime(data.get('start'), '%Y.%m.%d %H:%M:%S')
    end_time = dt.datetime.strptime(data.get('end'), '%Y.%m.%d %H:%M:%S')
    lon = float(data.get('lon'))
    lat = float(data.get('lat'))
    alt = float(data.get('alt'))

    orb = Orbital(satellite, 'tle.txt')

    content = f'Satellite {satellite}\n'
    content += f'Start date & time {start_time.strftime("%Y-%m-%d %H:%M:%S UTC")}\n'
    content += '\n'
    content += 'Time (UTC)\tAzimuth\tElevation\n'
    content += '\n'

    current_coords = orb.get_observer_look(start_time, lon, lat, alt)
    current_time = start_time
    shift = 0

    while current_time <= end_time:
        current_time = start_time + dt.timedelta(seconds=shift)
        content += f'{current_time.strftime("%H:%M:%S")}\t{current_coords[0]:.2f}\t{current_coords[1]:.2f}\n'
        current_coords = orb.get_observer_look(current_time, lon, lat, alt)
        shift += 1

    file = BytesIO(content.encode('utf-8'))

    return send_file(file, as_attachment=True, download_name='Траектория.txt', mimetype='text/plain')


if __name__ == '__main__':
    app.run()
