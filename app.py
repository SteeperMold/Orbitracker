from io import BytesIO
import datetime as dt
from flask import Flask, render_template, request, send_file, redirect
from pyorbital.orbital import Orbital
from calculations import OrbCalculator
from forms.user import RegisterForm, LoginForm, EditProfileForm, EditGeopositionForm
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


@app.route('/find_object', methods=['GET', 'POST'])
def get_timetable():
    form = ObservationPointCoordsForm()

    if form.validate_on_submit():
        lat = form.lat.data
        lon = form.lon.data
        alt = form.alt.data
        min_elevation = form.min_elevation.data
        min_apogee = form.min_apogee.data
        start_time = form.start_time.data
        duration = form.duration.data

        passes = OrbCalculator.get_passes(lat, lon, alt, min_elevation, min_apogee, start_time, duration)

        return render_template('found_objects.html', passes=passes, lon=lon, lat=lat, alt=alt, active_tab='find_object')
    return render_template('find_object.html', form=form, active_tab='find_object')


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
            return render_template('register.html', message="Такой пользователь уже есть",
                                   form=form, active_tab='register')

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
    app.run()
