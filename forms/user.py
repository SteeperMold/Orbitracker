from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField
from wtforms.validators import DataRequired


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
