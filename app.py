from io import BytesIO
import datetime as dt
from flask import Flask, render_template, request, send_file, redirect, session, jsonify
from pyorbital.orbital import Orbital
from calculations import OrbCalculator, SATELLITES
import geoip2.database
from forms.user import RegisterForm, LoginForm, EditProfileForm, EditGeopositionForm
from forms.coords_form import ObservationPointCoordsForm, PassesSettingsForm
from data import db_session
from data.users import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
def index():
    return redirect('/object/METEOR-M2%203')


@app.route('/passes', methods=['GET'])
def get_timetable():
    # Получаем пользователя если он зарегистрирован
    user = None
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()

    # Получаем координаты пользователя по айпи
    try:
        reader = geoip2.database.Reader('db/GeoLite2-City.mmdb')
        response = reader.city(request.remote_addr)
        ip_lat = response.location.latitude
        ip_lon = response.location.longitude
    except geoip2.errors.AddressNotFoundError:
        ip_lat = ip_lon = None

    # Если пользователь сохранил свои координаты или получилось определить их по айпи,
    # отображаем форму без ввода координат
    if (user and user.lon and user.lat and user.alt) or (ip_lat and ip_lon):
        form = PassesSettingsForm(request.args)
    else:
        form = ObservationPointCoordsForm(request.args)

    if form.validate():
        # Если форма была с вводом координат, то достаем их из формы
        if isinstance(form, ObservationPointCoordsForm):
            lat = form.lat.data
            lon = form.lon.data
            alt = form.alt.data
        else:
            lat = user.lat or ip_lat
            lon = user.lon or ip_lon
            alt = user.alt or 0

        min_elevation = form.min_elevation.data
        min_apogee = form.min_apogee.data
        start_time = form.start_time.data
        duration = form.duration.data

        passes = OrbCalculator.get_passes(lat, lon, alt, min_elevation, min_apogee, start_time, duration)

        return render_template('passes.html', passes=passes, lon=lon, lat=lat, alt=alt)
    return render_template('get_passes.html', form=form)


@app.route('/make-pass-trajectory', methods=['GET'])
def make_pass_trajectory():
    """
    Расчитывает траекторию спутника и сохраняет в сессию, чтобы при обновлении страницы
    не нужно было заново расчитывать координаты
    """
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

    # Для упрощения вычислений, расчитываем координаты с шагом 20 секунд
    for shift in range(0, (end_time - max(start_time, current_time)).seconds, 20):
        shifted_time = max(start_time, current_time) + dt.timedelta(seconds=shift)

        # Расчитываем абсолютные координаты спутника
        satellite_lon, satellite_lat, satellite_alt = orb.get_lonlatalt(shifted_time)
        absolute_trajectory.append([satellite_lon, satellite_lat, satellite_alt])

        # Расчитываем координаты спутника на небе относительно наблюдателя
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
    """
    Достать траекторию спутника из сессии
    """
    return jsonify({'absolute_trajectory': session['absolute_trajectory'],
                    'viewer_trajectory': session['viewer_trajectory'],
                    'lat': session['lat'], 'lon': session['lon'],
                    'start_time': session['start_time'], 'end_time': session['end_time']}), 200


@app.route('/get-viewer-coords', methods=['GET'])
def get_viewer_coords():
    """
    Расчитать текущие координаты спутника относительно наблюдателя, чтобы обновить их в браузере
    """
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

    content = f'Спутник {satellite}\n'
    content += f'Начальная дата и время {start_time.strftime("%Y-%m-%d %H:%M:%S UTC")}\n'
    content += '\n'
    content += 'Время (UTC)\tАзимут\tЭлевация\n'
    content += '\n'

    for shift in range((end_time - start_time).seconds):
        current_time = start_time + dt.timedelta(seconds=shift)
        azimuth, elevation = orb.get_observer_look(current_time, lon, lat, alt)
        content += f'{current_time.strftime("%H:%M:%S")}\t{azimuth:.2f}\t{elevation:.2f}\n'

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

    # Возвращаем подходящие названия спутников пользователю, чтобы тот выбрал нужный
    return render_template('find_object.html', satellites=satellites)


@app.route('/object/<name>', methods=['GET'])
def track_object(name):
    start_time = dt.datetime.now(tz=dt.timezone.utc)

    orb = Orbital(name, 'tle.txt')

    trajectory = []
    # Расчитываем траекторию за час до этой секудны, и на час после,
    # примерно один виток вокруг Земли
    for shift in range(-60, 60):
        lon, lat, alt = orb.get_lonlatalt(start_time + dt.timedelta(minutes=shift))
        trajectory.append((lon, lat, alt))

    satellite_lon, satellite_lat, satellite_alt = orb.get_lonlatalt(start_time)

    # Получаем координаты пользователя, чтобы отобразить его местонахождение на карте
    user_lat = user_lon = None
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        user_lat = user.lat
        user_lon = user.lon

    if not user_lat and not user_lon:
        try:
            reader = geoip2.database.Reader('db/GeoLite2-City.mmdb')
            response = reader.city(request.remote_addr)
            user_lat = response.location.latitude
            user_lon = response.location.longitude
        except geoip2.errors.AddressNotFoundError:
            user_lat = user_lon = None

    return render_template('orbit.html', sat=name, trajectory=trajectory, user_lat=user_lat, user_lon=user_lon,
                           satellite_lat=satellite_lat, satellite_lon=satellite_lon, satellite_alt=satellite_alt)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(user_id)
    return user


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


@app.route('/api/coords', methods=['GET'])
def coords():
    """
    Получение текущих абсолютных координат спутника
    """
    satellite = request.args.get('sat')
    time = request.args.get('time')
    if time:
        dt.datetime.strptime(f"{request.args.get('time')} +0000", '%Y-%m-%d %H:%M:%S %z')

    if satellite not in SATELLITES:
        return jsonify({'error': 'satellite not found'}), 200

    orb = Orbital(satellite, 'tle.txt')

    lon, lat, alt = orb.get_lonlatalt(time or dt.datetime.now(tz=dt.timezone.utc))

    return jsonify({'lon': lon, 'lat': lat, 'alt': alt}), 200


@app.route('/api/trajectory', methods=['GET'])
def trajectory():
    """
    Получение текущих координат спутника на небе относительно наблюдателя
    """
    satellite = request.args.get('sat')
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    alt = float(request.args.get('alt'))
    time = request.args.get('time')
    if time:
        dt.datetime.strptime(f"{request.args.get('time')} +0000", '%Y-%m-%d %H:%M:%S %z')

    orb = Orbital(satellite, 'tle.txt')
    azimuth, elevation = orb.get_observer_look(time or dt.datetime.now(tz=dt.timezone.utc), lon, lat, alt)

    return jsonify({'azimuth': azimuth, 'elevation': elevation}), 200


@app.route('/api/passes', methods=['GET'])
def passes():
    """
    Получение всех пролетов всех спутников за указанный период времени
    """
    lon = float(request.args.get('lon'))
    lat = float(request.args.get('lat'))
    alt = float(request.args.get('alt'))
    start_time = dt.datetime.strptime(f"{request.args.get('time')} +0000", '%Y-%m-%d %H:%M:%S %z')
    duration = int(request.args.get('duration'))

    passes = OrbCalculator.get_passes(lat, lon, alt, 0, 0, start_time, duration)

    return jsonify({'passes': passes}), 200


if __name__ == '__main__':
    db_session.global_init("db/orbitracker.db")
    app.run(host='0.0.0.0')
