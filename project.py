# Imports
from flask import Flask, render_template, \
    url_for, request, redirect,\
    flash, jsonify, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import *
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import os
import random
import string
import datetime
import json
import httplib2
import requests
# Import login_required from login_decorator.py
from login_decorator import login_required

# Flask instance
app = Flask(__name__)


# GConnect CLIENT_ID

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item-Catalog"


# Connect to database
engine = create_engine('sqlite:///catalog.db',
                       connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine
# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()
# categories is a global variable need to use in entire application
categories = session.query(Category).order_by(asc(Category.name))


# Login - Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                                  string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state, categories=categories)

@app.route('/users')
def showUsers():
    users = session.query(User).order_by(asc(User.id))
    return render_template('users.html', users = users,categories = categories)

# GConnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Gathers data from Google Sign In API and places
    it inside a session variable.
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is'
                                            'already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    # data = answer.json()
    data = json.loads(answer.text)
    try:
        login_session['username'] = data['name']
        login_session['picture'] = data['picture']
        login_session['email'] = data['email']
    except:
        login_session['username'] = "Google User"
        login_session['picture'] = "http://tiny.cc/lz6m2y"
        login_session['email'] = "Google Email"

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    ' -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception as e:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    try:
        result['status'] == '200'
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = redirect(url_for('showCatalog'))
        flash("You are now logged out.")
        return response
    except Exception as e:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'+e, 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Flask Routing

# Homepage
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    items = session.query(Items).order_by(desc(Items.date)).limit(5)
    return render_template('catalog.html',
                           categories=categories,
                           items=items)

# Category Items


@app.route('/catalog/<path:category_name>/items/')
def showCategory(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Items).filter_by(
        category=category).order_by(asc(Items.name)).all()
    count = session.query(Items).filter_by(category=category).count()
    creator = getUserInfo(category.user_id)
    if 'username' not in login_session or \
       creator.id != login_session['user_id']:
        return render_template('public_items.html',
                               category=category.name,
                               categories=categories,
                               items=items,
                               count=count)
    else:
        user = getUserInfo(login_session['user_id'])
        return render_template('items.html',
                               category=category.name,
                               categories=categories,
                               items=items,
                               count=count,
                               user=user)
# Add a category


@app.route('/catalog/addcategory', methods=['GET', 'POST'])
@login_required
def addCategory():
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'],
            user_id=login_session['user_id'])
        # print(newCategory)
        session.add(newCategory)
        session.commit()
        flash('Category Successfully Added!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('addcategory.html', categories=categories)


# Edit a category
@app.route('/catalog/<path:category_name>/c_edit', methods=['GET', 'POST'])
@login_required
def editCategory(category_name):
    editedCategory = session.query(
        Category).filter_by(name=category_name).one()
    category = session.query(Category).filter_by(name=category_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editedCategory.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot edit this Category."
              "This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    # POST methods
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
        session.add(editedCategory)
        session.commit()
        flash('Category Item Successfully Edited!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('editcategory.html',
                               categories=categories,
                               category=category)


# Delete a category
@app.route('/catalog/<path:category_name>/c_delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_name):
    categoryToDelete = session.query(
        Category).filter_by(name=category_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(categoryToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot delete this Category."
              "This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        session.delete(categoryToDelete)
        session.commit()
        flash('{0} Category Successfully Deleted! '
              .format(categoryToDelete.name))
        return redirect(url_for('showCatalog'))
    else:
        return render_template('deletecategory.html',
                               category=categoryToDelete,
                               categories=categories)


# Add an item
@app.route('/catalog/add', methods=['GET', 'POST'])
@login_required
def addItem():
    if request.method == 'POST':
        newItem = Items(
            name=request.form['name'],
            description=request.form['description'],
            picture=request.form['picture'],
            category=session.query(
                Category).filter_by(name=request.form['category']).one(),
            date=datetime.datetime.now(),
            user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('Item Successfully Added!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('additem.html',
                               categories=categories)


# Edit an item
@app.route('/catalog/<path:category_name>/'
           '<path:item_name>/i_edit', methods=['GET', 'POST'])
@login_required
def editItem(category_name, item_name):
    editedItem = session.query(Items).filter_by(name=item_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editedItem.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot edit this item. "
              "This item belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    # POST methods
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['picture']:
            editedItem.picture = request.form['picture']
        if request.form['category']:
            category = session.query(Category).filter_by(
                name=request.form['category']).one()
            editedItem.category = category
        time = datetime.datetime.now()
        editedItem.date = time
        session.add(editedItem)
        session.commit()
        flash('Category Item Successfully Edited!')
        return redirect(url_for('showCategory',
                                category_name=editedItem.category.name))
    else:
        return render_template('edititem.html',
                               item=editedItem,
                               categories=categories)


# Delete an item
@app.route('/catalog/<path:category_name>/<path:item_name>/i_delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_name, item_name):
    itemToDelete = session.query(Items).filter_by(name=item_name).one()
    category = session.query(Category).filter_by(name=category_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(itemToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot delete this item. "
              "This item belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted! '+itemToDelete.name)
        return redirect(url_for('showCategory',
                                category_name=category.name))
    else:
        return render_template('deleteitem.html',
                               item=itemToDelete, categories=categories)

# JSON
@app.route('/catalog/JSON')
def allItemsJSON():
    categories = session.query(Category).all()
    category_dict = [c.serialize for c in categories]
    for c in range(len(category_dict)):
        items = [i.serialize for i in session.query(
                 Items).filter_by(category_id=category_dict[c]["id"]).all()]
        if items:
            category_dict[c]["Item"] = items
    return jsonify(Category=category_dict)


@app.route('/catalog/categories/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/catalog/items/JSON')
def itemsJSON():
    items = session.query(Items).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog/<path:category_name>/items/JSON')
def categoryItemsJSON(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Items).filter_by(category=category).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog/<path:category_name>/<path:item_name>/JSON')
def ItemJSON(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Items).filter_by(
        name=item_name, category=category).one()
    return jsonify(item=[item.serialize])


# Always at end of file !Important!
if __name__ == '__main__':
    app.secret_key = 'APP_SECRET_KEY'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
