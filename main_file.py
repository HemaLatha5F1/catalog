# !/usr/bin/env python3

from flask import (
    Flask,
    flash,
    render_template,
    request,
    url_for,
    redirect,
    jsonify
    )

import sys

from sqlalchemy import(
    Column,
    ForeignKey,
    Integer,
    String
    )

from sqlalchemy.ext.declarative import declarative_base
from flask import make_response

from sqlalchemy.orm import relationship, backref

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

from sqlalchemy import create_engine


from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import os
import random
import string
import httplib2
import json
import requests


app = Flask(__name__)

Base = declarative_base()


class Admin(Base):
    __tablename__ = "admin"
    admin_id = Column(Integer, primary_key=True)
    admin_mail = Column(String(100), nullable=False)


class HeadWear(Base):
    __tablename__ = "headwear"
    headwear_id = Column(Integer, primary_key=True)
    headwear_name = Column(String(100), nullable=False)
    headwear_admin = Column(Integer, ForeignKey('admin.admin_id'))
    headwear_relation = relationship(Admin)


class Items(Base):
    __tablename__ = "items"
    item_id = Column(Integer, primary_key=True)
    item_name = Column(String(100), nullable=False)
    item_price = Column(Integer, nullable=False)
    item_brand = Column(String(100), nullable=False)
    item_image = Column(String(1000), nullable=False)
    headwear_id = Column(Integer, ForeignKey('headwear.headwear_id'))
    item_relation = relationship(
        HeadWear,
        backref=backref("headwear", cascade="all,delete"))
    # for json

    @property
    def serialize(self):
        return {
            'id': self.item_id,
            'name': self.item_name,
            'price': self.item_price,
            'brand': self.item_brand,
            'image': self.item_image,
        }
# end of line
engine = create_engine('sqlite:///headwear.db')
Base.metadata.create_all(engine)

session = scoped_session(sessionmaker(bind=engine))


CLIENT_DATA = json.loads(open("client_secrets.json").read())
CLIENT_ID = CLIENT_DATA["web"]['client_id']


@app.route('/read')
def read():
    headwear = session.query(Items).all()
    msg = ""
    for each in headwear:
        msg += str(each.item_name)
    return msg


@app.route('/')
@app.route('/home')
def home():
    """Home page for the website"""
    items = session.query(Items).all()
    return render_template(
        'showitems.html',
        Items=items, hasRecent=True, category_id=None)


@app.route('/category', methods=['GET'])
def showcategory():
    """Display ccategories list"""
    if request.method == 'GET':
        category_list = session.query(HeadWear).all()
        return render_template('scategory.html', categories=category_list)


# gives the json data
@app.route('/Headwear/all.json')
def all_json():
    rows = session.query(Items).all()
    return jsonify(Rows=[each.serialize for each in rows])


# to create new category
@app.route('/category/new', methods=['GET', 'POST'])
def newcategory():
    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('new_category.html')
    else:
        category_name = request.form['category_name']
        if category_name:
            admin = session.query(Admin).filter_by(
                admin_mail=login_session['email']
                ).one_or_none()
            if admin is None:
                return redirect(url_for('home'))
            admin_id = admin.admin_id
            new_headwear = HeadWear(
                headwear_name=category_name,
                headwear_admin=admin_id
                )
            session.add(new_headwear)
            session.commit()
            flash('Your Item is added')
            return redirect(url_for('home'))
        else:
            flash('Category not added successfully')
            return redirect(url_for('home'))


@app.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editcategory(category_id):
    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))
    admin = session.query(Admin).filter_by(
        admin_mail=login_session['email']
        ).one_or_none()
    if admin is None:
        flash("Invalid user ")
        return redirect(url_for('home'))
    headwear = session.query(HeadWear).filter_by(
        headwear_id=category_id
        ).one_or_none()
    if headwear is None:
        flash('Category is not available')
        return redirect(url_for('home'))
    login_admin_id = admin.admin_id
    admin_id = headwear.headwear_admin
    if login_admin_id != admin_id:
        flash('You are not allowed to edit this category')
        return redirect(url_for('home'))

    if request.method == 'POST':
        category_name = request.form['category_name']
        headwear.headwear_name = category_name
        session.add(headwear)
        session.commit()
        flash('Category updated successfully')
        return redirect(url_for('home'))
    else:
        headwear = session.query(HeadWear).filter_by(
            headwear_id=category_id
            ).one_or_none()
        return render_template(
            'edit_category.html',
            headwear_name=headwear.headwear_name,
            id_category=category_id)


@app.route('/category/<int:category_id>/delete')
def deletecategory(category_id):

    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))
    admin = session.query(Admin).filter_by(
        admin_mail=login_session['email']
        ).one_or_none()
    if admin is None:
        flash("Invalid user")
        return redirect(url_for('home'))

    headwear = session.query(HeadWear).filter_by(
        headwear_id=category_id
        ).one_or_none()
    if headwear is None:
        flash('Category is not available')
        return redirect(url_for('home'))
    login_admin_id = admin.admin_id
    admin_id = headwear.headwear_admin
    if login_admin_id != admin_id:
        flash('You are not allowed to delete this category')
        return redirect(url_for('home'))
    name = headwear.headwear_name
    session.delete(headwear)
    session.commit()
    flash('Deleted successfully '+str(name))
    return redirect(url_for('home'))


@app.route('/Headwear/category/<int:category_id>.json')
def one_category_json(category_id):
    catsingle = session.query(Items).filter_by(headwear_id=category_id).all()
    return jsonify(Catsingle=[each.serialize for each in catsingle])


@app.route('/category/items')
def showitems():
    if request.method == 'GET':
        category_list = session.query(Items).filter_by(headwear_id=1).all()
    return render_template(
        'showitems.html',
        categories=category_list,
        hasRecent=False)


@app.route('/latestitems')
def latestitems():
    if request.method == 'GET':
        category_list = session.query(Items).all()
    return render_template('latestitems.html', categories=category_list)


@app.route('/category/<int:category_id>/items')
def showcategoryitems(category_id):
    if request.method == 'GET':
        items = session.query(Items).filter_by(headwear_id=category_id).all()
    return render_template(
        'showitems.html', Items=items, category_id=category_id)


@app.route(
    '/category/<int:category_id>/items/<int:itemid>',
    methods=['GET', 'POST']
    )
def itemdetails(category_id, itemid):
    if request.method == 'GET':
        item = session.query(Items).filter_by(
            headwear_id=category_id,
            item_id=itemid
            ).one_or_none()
        return render_template(
            'item_details.html',
            iname=item.item_name,
            iprice=item.item_price,
            ibrand=item.item_brand,
            image=item.item_image
            )


@app.route('/category/<int:categoryid>/items/new', methods=['GET', 'POST'])
def newitem(categoryid):
    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))

    admin = session.query(Admin).filter_by(
        admin_mail=login_session['email']
        ).one_or_none()
    if admin is None:
        flash("Invalid user")
        return redirect(url_for('home'))

    categoryname = session.query(HeadWear).filter_by(
        headwear_id=categoryid
        ).one_or_none()
    if not categoryname:
        flash('Category not found')
        return redirect(url_for('home'))

    login_admin_id = admin.admin_id
    admin_id = categoryname.headwear_admin

    if login_admin_id != admin_id:
        flash('Your not correct person')
        return redirect(url_for('home'))
    if request.method == 'GET':
        flash('You are ready to add item in '+categoryname.headwear_name)
        return render_template('additem.html', cat_id=categoryid)
    else:
        name = request.form['iname']
        image = request.form['iimage']
        price = request.form['iprice']
        brand = request.form['ibrand']
        sid = categoryid
        new_item = Items(
            item_name=name,
            item_price=price,
            item_brand=brand,
            item_image=image,
            headwear_id=sid
            )
        session.add(new_item)
        session.commit()
        flash('Your item added')
        return redirect(url_for('home'))


@app.route(
    '/category/<int:categoryid>/items/<int:itemid>/edit',
    methods=['GET', 'POST']
    )
def edititem(categoryid, itemid):
    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))

    admin = session.query(Admin).filter_by(
        admin_mail=login_session['email']
        ).one_or_none()
    if admin is None:
        flash("Invalid user")
        return redirect(url_for('home'))

    categoryname = session.query(HeadWear).filter_by(
        headwear_id=categoryid
        ).one_or_none()
    if not categoryname:
        flash('Category not found')
        return redirect(url_for('home'))

    item = session.query(Items).filter_by(
        item_id=itemid,
        headwear_id=categoryid
        ).one_or_none()
    if not item:
        flash('Invalid item')
        return redirect(url_for('home'))

    login_admin_id = admin.admin_id
    admin_id = categoryname.headwear_admin

    if login_admin_id != admin_id:
        flash('Your not correct person to edit this item')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['iname']
        image = request.form['iimage']
        price = request.form['iprice']
        brand = request.form['ibrand']
        item = session.query(Items).filter_by(
            headwear_id=categoryid,
            item_id=itemid
            ).one_or_none()
        if item:
            item.item_name = name
            item.item_image = image
            item.item_price = price
            item.item_brand = brand
        else:
            flash('No items')
            return redirect(url_for('home'))
        session.add(item)
        session.commit()
        flash('Item updated successfully')
        return redirect(url_for('home'))
    else:
        edit = session.query(Items).filter_by(item_id=itemid).one_or_none()
        if edit:
            return render_template(
                'edit_item.html',
                iname=edit.item_name,
                iprice=edit.item_price,
                ibrand=edit.item_brand,
                iimage=edit.item_image,
                catid=categoryid,
                iid=itemid)
        else:
            return 'no elements'


@app.route('/category/<int:categoryid>/items/<int:itemid>/delete')
def deleteitem(categoryid, itemid):
    if 'email' not in login_session:
        flash("Please login...")
        return redirect(url_for('login'))
    admin = session.query(Admin).filter_by(
        admin_mail=login_session['email']
        ).one_or_none()
    if admin is None:
        flash("Invalid user")
        return redirect(url_for('home'))

    categoryname = session.query(HeadWear).filter_by(
        headwear_id=categoryid
        ).one_or_none()
    if not categoryname:
        flash('Category not found')
        return redirect(url_for('home'))

    item = session.query(Items).filter_by(
        headwear_id=categoryid,
        item_id=itemid
        ).one_or_none()
    if not item:
        flash('Invalid item')
        return redirect(url_for('home'))

    login_admin_id = admin.admin_id
    admin_id = categoryname.headwear_admin

    if login_admin_id != admin_id:
        flash('Your not correct person to delete this item')
        return redirect(url_for('home'))
    item = session.query(Items).filter_by(item_id=itemid).one_or_none()
    if item:
        name = item.item_name
        session.delete(item)
        session.commit()
        flash('Deleted successfully '+str(name))
        return redirect(url_for('home'))
    else:
        flash('Item not found')
        return redirect(url_for('home'))
# login routing


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# it helps the user to loggedin and display flash profile

# GConnect


@app.route('/gconnect', methods=['POST', 'GET'])
def gConnect():
    if request.args.get('state') != login_session['state']:
        response.make_response(json.dumps('Invalid State paramenter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    request.get_data()
    code = request.data.decode('utf-8')

    # Obtain authorization code

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps("""Failed to upgrade the authorisation code"""), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.

    access_token = credentials.access_token
    myurl = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
        % access_token)
    header = httplib2.Http()
    result = json.loads(header.request(myurl, 'GET')[1].decode('utf-8'))

    # If there was an error in the access token info, abort.

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps(
                            """Token's user ID does not
                            match given user ID."""),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.

    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps(
            """Token's client ID
            does not match app's."""),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'
            ), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info

    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    # ADD PROVIDER TO LOGIN SESSION

    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    admin_id = userID(login_session['email'])
    if not admin_id:
        admin_id = createNewUser(login_session)
    login_session['admin_id'] = admin_id
    flash("Successfull Login %s" % login_session['email'])
    return "Verified Successfully"


def createNewUser(login_session):
    email = login_session['email']
    newAdmin = Admin(admin_mail=email)
    session.add(newAdmin)
    session.commit()
    admin = session.query(Admin).filter_by(admin_mail=email).first()
    admin_Id = admin.admin_id
    return admin_Id


def userID(admin_mail):
    try:
        admin = session.query(Admin).filter_by(admin_mail=admin_mail).one()
        return admin.admin_id
    except Exception as e:
        print(e)
        return None
# Gdisconnect


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    del login_session['email']
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps(
            'Current user not connected.'
            ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    header = httplib2.Http()
    result = header.request(url, 'GET')[0]

    if result['status'] == '200':

        # Reset the user's session.

        del login_session['access_token']
        del login_session['gplus_id']
        response = redirect(url_for('home'))
        response.headers['Content-Type'] = 'application/json'
        flash("successfully signout", "success")
        return response
    else:

        # if given token is invalid, unable to revoke token
        response = make_response(json.dumps('Failed to revoke token for user'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/logout')
def logout():
    if 'email' in login_session:
        flash('you loggeed out')
        return gdisconnect()
    flash('You are already logout.')
    return redirect(url_for('login'))


@app.context_processor
def inject_all():
    category = session.query(HeadWear).all()
    return dict(mycategories=category)

if __name__ == '__main__':
    app.secret_key = "catalog@123"
    app.run(debug=True, host="localhost", port=5000)
