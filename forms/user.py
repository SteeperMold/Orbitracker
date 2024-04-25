from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField, FloatField
from wtforms.validators import DataRequired, InputRequired, NumberRange


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired(message='Это обязательное поле')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Это обязательное поле')])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired(message='Это обязательное поле')])
    name = StringField('Имя пользователя', validators=[DataRequired(message='Это обязательное поле')])
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired(message='Это обязательное поле')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Это обязательное поле')])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class EditProfileForm(FlaskForm):
    name = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class EditGeopositionForm(FlaskForm):
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
    submit = SubmitField('Сохранить')
