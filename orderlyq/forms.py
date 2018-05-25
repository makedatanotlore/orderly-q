from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, RadioField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from orderlyq.models import User, Block
from orderlyq import db, bcrypt
import json


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class UpdateAccountForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already taken. Please choose a different one.')


class CreateBlockForm(FlaskForm):
    data = StringField('Data', validators=[DataRequired(), Length(min=2, max=140)])
    submit = SubmitField("Queue Up")


class ApplicationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=20)])
    street = StringField('Street', validators=[DataRequired(), Length(min=2, max=20)])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=20)])
    zip_code = StringField('ZIP', validators=[DataRequired(),  Length(min=5, max=5)])
    submit = SubmitField('Send Application')

class UpdateApplicationForm(FlaskForm):
    application_no = StringField('Application #', validators=[DataRequired(), Length(min=5, max=5)])
    status = RadioField('Status', validators=[DataRequired()], choices=[('DOING', 'Doing'), ('DONE', 'Done')])
    street = StringField('Street', validators=[DataRequired(), Length(min=2, max=20)])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=20)])
    zip_code = StringField('ZIP', validators=[DataRequired(),  Length(min=5, max=5)])
    submit = SubmitField('Update Application')

    def validate_application_no(self, application_no):
        blocks = [block for block in db.session.query(Block).order_by(Block.timestamp.desc())]
        found_application = None
        for block in blocks:
            json_data = json.loads(block.data)
            for application in json_data:
                if application_no.data == application[0]:
                    found_application = application
                    break
        if found_application:
            if not bcrypt.check_password_hash(found_application[1], current_user.username):
                raise ValidationError('You are not allowed to update this application.')
        else:
            raise ValidationError('No application with that number exists.')