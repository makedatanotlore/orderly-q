import os
import secrets

from PIL import Image
from flask import render_template, flash, redirect, url_for, request
from orderlyq.forms import RegistrationForm, LoginForm, UpdateAccountForm, ApplicationForm, UpdateApplicationForm
from orderlyq import app, db, bcrypt
from flask_login import login_user, current_user, logout_user, login_required
from orderlyq.models import User, Block
import hashlib as hasher
from datetime import datetime
from collections import namedtuple
import random
import json

Application = namedtuple('Application', 'application_no password name street city zip_code status')


def hash_block(index, timestamp, data, previous_hash):
    sha = hasher.sha256()
    sha.update(str(index).encode('utf-8') +
               str(timestamp).encode('utf-8') +
               str(data).encode('utf-8') +
               str(previous_hash).encode('utf-8'))
    return sha.hexdigest()


data_to_send = []


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    form = ApplicationForm()
    blocks = [block for block in db.session.query(Block).order_by(Block.timestamp.desc())]
    if form.validate_on_submit():
        application_no = str(random.randint(1, 100000)).zfill(5)
        name = form.name.data
        street = form.street.data
        city = form.city.data
        zip_code = form.zip_code.data
        hashed_password = bcrypt.generate_password_hash(current_user.username).decode('utf-8')
        application = Application(application_no=application_no,
                                  name=name,
                                  street=street,
                                  city=city,
                                  zip_code=zip_code,
                                  password=hashed_password,
                                  status="TODO")
        data_to_send.append(application)
        if len(data_to_send) >= 3:
            create_block()

        flash('Your application has been submitted!', 'success')
        return redirect(url_for('home'))
    return render_template('home.html', form=form, blocks=blocks, bcrypt=bcrypt, json=json)

@app.route('/application', methods=['GET', 'POST'])
@login_required
def application():
    form = UpdateApplicationForm()
    blocks = [block for block in db.session.query(Block).order_by(Block.timestamp.desc())]
    if form.validate_on_submit():
        found_application = None
        for block in blocks:
            json_data = json.loads(block.data)
            for a in json_data:
                if form.application_no.data == a[0]:
                    found_application = a
                    break
        application_no = form.application_no.data
        name = found_application[2]
        street = form.street.data
        city = form.city.data
        zip_code = form.zip_code.data
        hashed_password = found_application[1]
        status = form.status.data
        application = Application(application_no=application_no,
                                  name=name,
                                  street=street,
                                  city=city,
                                  zip_code=zip_code,
                                  password=hashed_password,
                                  status=status)
        data_to_send.append(application)
        if len(data_to_send) >= 3:
            create_block()

        flash('Your application has been updated!', 'success')
        return redirect(url_for('home'))
    return render_template('application.html', form=form, blocks=blocks, bcrypt=bcrypt, json=json)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title="Sign up", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title="Sign in", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/images/profile_pics', picture_fn)

    output_size = (125, 125)
    image = Image.open(form_picture)
    image.thumbnail(output_size)

    image.save(picture_path)
    return picture_fn


@app.route('/account',  methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file

        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.email.data = current_user.email

    image_file = url_for('static', filename='images/profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


def create_genesis_block():
    password = bcrypt.generate_password_hash("g").decode('utf-8')
    application = Application(application_no="00000",
                              name="Genesis Block",
                              street="Genesis Block",
                              city="Genesis Block",
                              zip_code="00000",
                              password=password,
                              status="NONE")
    data = json.dumps([application])
    index = 0
    timestamp = datetime.utcnow()
    previous_hash = "0"
    new_hash = hash_block(index, timestamp, data, previous_hash)
    genesis_block = Block(index=index, timestamp=timestamp, data=data, previous_hash=previous_hash, hash=new_hash)
    db.session.add(genesis_block)
    db.session.commit()
    print(data)


def create_block():
    json_data = json.dumps(data_to_send)
    last_block = db.session.query(Block).order_by(Block.index.desc()).first()
    data = json_data
    index = last_block.index
    index += 1
    timestamp = datetime.utcnow()
    new_hash = hash_block(index, timestamp, data, last_block.hash)
    new_block = Block(index=index, timestamp=timestamp, data=data, previous_hash=last_block.hash,
                      hash=new_hash)
    db.session.add(new_block)
    db.session.commit()
    data_to_send.clear()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
