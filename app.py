from io import BytesIO
import datetime as dt
from flask import Flask, render_template, request, send_file, redirect, session, jsonify
from pyorbital.orbital import Orbital
from calculations import OrbCalculator, SATELLITES
import geoip2.database
from forms.user import RegisterForm, LoginForm, EditProfileForm
from forms.coords_form import ObservationPointCoordsForm
from data import db_session
from data.users import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
def index():
    return render_template('index.html', active_tab='home')


@app.route('/passes', methods=['GET'])
def get_timetable():
    form = ObservationPointCoordsForm(request.args)

    if form.validate():
        lat = form.lat.data
        lon = form.lon.data
        alt = form.alt.data
        min_elevation = form.min_elevation.data
        min_apogee = form.min_apogee.data
        start_time = form.start_time.data
        duration = form.duration.data

        passes = OrbCalculator.get_passes(lat, lon, alt, min_elevation, min_apogee, start_time, duration)

        return render_template('passes.html', passes=passes, lon=lon, lat=lat, alt=alt)
    return render_template('get_passes.html', form=form)


@app.route('/make-pass-trajectory', methods=['GET'])
def make_pass_trajectory():
    satellite = request.args.get('satellite')
    start_time = dt.datetime.strptime(f'{request.args.get("start")} +0000', '%Y.%m.%d %H:%M:%S %z')
    end_time = dt.datetime.strptime(f'{request.args.get("end")} +0000', '%Y.%m.%d %H:%M:%S %z')
    lon = float(request.args.get('lon'))
    lat = float(request.args.get('lat'))
    alt = float(request.args.get('alt'))

    current_time = dt.datetime.now(tz=dt.timezone.utc)

    orb = Orbital(satellite, 'tle.txt')

    absolute_trajectory = []
    viewer_trajectory = []

    for shift in range(0, (end_time - max(start_time, current_time)).seconds, 15):
        shifted_time = max(start_time, current_time) + dt.timedelta(seconds=shift)

        satellite_lon, satellite_lat, satellite_alt = orb.get_lonlatalt(shifted_time)
        absolute_trajectory.append([satellite_lon, satellite_lat])

        azimuth, elevation = orb.get_observer_look(shifted_time, lon, lat, alt)
        viewer_trajectory.append([azimuth, elevation])

    session['absolute_trajectory'] = absolute_trajectory
    session['viewer_trajectory'] = viewer_trajectory
    session['lat'] = lat
    session['lon'] = lon
    session['alt'] = alt
    session['start_time'] = start_time.strftime('%Y.%m.%d %H:%M:%S')
    session['end_time'] = end_time.strftime('%Y.%m.%d %H:%M:%S')
    session['satellite'] = satellite

    return ''


@app.route('/get-pass-trajectory', methods=['GET'])
def get_pass_trajectory():
    return jsonify({'absolute_trajectory': session['absolute_trajectory'],
                    'viewer_trajectory': session['viewer_trajectory'],
                    'lat': session['lat'], 'lon': session['lon'],
                    'start_time': session['start_time'], 'end_time': session['end_time']}), 200


@app.route('/get-viewer-coords', methods=['GET'])
def get_viewer_coords():
    satellite = session['satellite']
    start_time = dt.datetime.strptime(f'{session["start_time"]} +0000', '%Y.%m.%d %H:%M:%S %z')
    end_time = dt.datetime.strptime(f'{session["end_time"]} +0000', '%Y.%m.%d %H:%M:%S %z')
    current_time = dt.datetime.now(tz=dt.timezone.utc)
    lat = session['lat']
    lon = session['lon']
    alt = session['alt']

    if not start_time <= current_time <= end_time:
        return jsonify({'error': 'wrong time'}), 200

    orb = Orbital(satellite, 'tle.txt')

    satellite_lon, satellite_lat, satellite_alt = orb.get_lonlatalt(current_time)
    azimuth, elevation = orb.get_observer_look(current_time, lon, lat, alt)

    return jsonify({'lon': satellite_lon, 'lat': satellite_lat, 'azimuth': round(azimuth, 2),
                    'elevation': round(elevation, 2)}), 200


@app.route('/view-pass-trajectory', methods=['GET'])
def view_pass_trajectory():
    return render_template('trajectory.html')


@app.route('/download-trajectory', methods=['GET'])
def download_trajectory():
    satellite = request.args.get('satellite')
    start_time = dt.datetime.strptime(request.args.get('start'), '%Y.%m.%d %H:%M:%S')
    end_time = dt.datetime.strptime(request.args.get('end'), '%Y.%m.%d %H:%M:%S')
    lon = float(request.args.get('lon'))
    lat = float(request.args.get('lat'))
    alt = float(request.args.get('alt'))

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


@app.route('/find-object', methods=['GET'])
def find_object():
    query = request.args.get('query')

    if not query:
        return render_template('find_object.html')

    satellites = []
    for sat in SATELLITES:
        if query.lower() in sat.lower():
            satellites.append(sat)

    return render_template('find_object.html', satellites=satellites)


@app.route('/object/<name>', methods=['GET'])
def track_object(name):
    start_time = dt.datetime.now(tz=dt.timezone.utc)

    orb = Orbital(name, 'tle.txt')

    trajectory = []
    for shift in range(-1 * 60, 1 * 60):
        lon, lat, alt = orb.get_lonlatalt(start_time + dt.timedelta(minutes=shift))
        trajectory.append((lon, lat, alt))

    satellite_lon, satellite_lat, satellite_alt = orb.get_lonlatalt(start_time)

    try:
        reader = geoip2.database.Reader('db/GeoLite2-City.mmdb')
        response = reader.city(request.remote_addr)
        user_lat = response.location.latitude
        user_lon = response.location.longitude
    except geoip2.errors.AddressNotFoundError:
        user_lat = user_lon = None

    return render_template('orbit.html', trajectory=trajectory, user_lat=user_lat, user_lon=user_lon,
                           satellite_lat=satellite_lat, satellite_lon=satellite_lon, satellite_alt=satellite_alt)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():

        if form.password.data != form.password_again.data:
            return render_template('register.html', message="Пароли не совпадают",
                                   form=form, active_tab='register')

        db_sess = db_session.create_session()

        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', message="Такой пользователь уже есть", form=form)

        user = User(
            name=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()

        return redirect('/login')
    return render_template('register.html', form=form, active_tab='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form, active_tab='login')

    return render_template('login.html', form=form, active_tab='login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', active_tab='profile')


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()

        if user:
            user.name = form.name.data
            db_sess.commit()
            return redirect('/profile')

    return render_template('edit_profile.html', form=form, active_tab='profile')


@app.route('/edit_geoposition', methods=['GET', 'POST'])
@login_required
def edit_geoposition():
    form = EditGeopositionForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()

        if user:
            user.lat = form.lat.data
            user.lon = form.lon.data
            user.alt = form.alt.data
            db_sess.commit()
            return redirect('/profile')

    return render_template('edit_geoposition.html', form=form, active_tab='profile')


if __name__ == '__main__':
    db_session.global_init("db/orbitracker.db")
    app.run(host='0.0.0.0')
