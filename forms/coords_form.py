from flask_wtf import FlaskForm
from wtforms import SubmitField, FloatField, DateTimeLocalField, IntegerField
from wtforms.validators import NumberRange, InputRequired


class ObservationPointCoordsForm(FlaskForm):
    lat = FloatField('Широта', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=-90, max=90, message='Широта должна быть от %(min)s до %(max)s')
    ])
    lon = FloatField('Долгота', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=-180, max=180, message='Долгота должна быть от %(min)s до %(max)s')
    ])
    alt = FloatField('Высота над уровнем моря (в метрах)', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=0, message='Высота не может быть отрицательной')
    ])
    min_elevation = FloatField('Минимальная элевация спутника', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=0, max=90, message='Элевация должна быть от %(min)s до %(max)s')
    ])
    min_apogee = FloatField('Минимальная кульминация спутника', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=0, max=90, message='Кульминация должна быть от %(min)s до %(max)s')
    ])
    start_time = DateTimeLocalField('Время начала наблюдения (UTC)', format='%Y-%m-%dT%H:%M', validators=[
        InputRequired(message='Это обязательное поле')
    ])
    duration = IntegerField('Длительность наблюдения (в часах)', validators=[
        InputRequired(message='Это обязательное поле'),
        NumberRange(min=0, message='Длительность наблюдения не может быть отрицательной')
    ])
    submit = SubmitField('Получить расписание →')
