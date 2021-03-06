#! /usr/bin/env python3

import json
import random
import string
from functools import wraps

import httplib2
import requests
from flask import Flask, render_template, request, \
    redirect, jsonify, url_for, flash, make_response, \
    session as login_session
from oauth2client.client import FlowExchangeError, OAuth2WebServerFlow
from sqlalchemy import asc
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Todolist, ListItem, User, engine
from variables import google_web, main_app

state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                for x in range(32))

app = Flask(__name__)
app.secret_key = state

GOOGLE_CLIENT_ID = google_web.get('client_id')
APPLICATION_NAME = "Todolist List Application"

# Connect to Database and create database session
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    """
    If a user is logged in, perform the normal action.
    Otherwise, send them to the login.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(request.url)
        if 'username' not in login_session:
            flash(
                "The url %s is not available "
                "unless you are logged in!" % request.url
            )
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


@app.route('/login')
def show_login():
    login_session['state'] = state
    return render_template(
        'login.html',
        STATE=login_session['state'],
        google_web=google_web,
    )


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = OAuth2WebServerFlow(
            redirect_uri='postmessage',
            **google_web
        )
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
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
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
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = get_user_id(data["email"])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions


def create_user(login_session_dict):
    new_user = User(
        name=login_session_dict['username'],
        email=login_session_dict['email'],
        picture=login_session_dict['picture']
    )
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(
        email=login_session_dict['email']
    ).one()
    return user.id


def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
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
    if result['status'] == '200':
        remove_session()
        response = make_response(json.dumps('Successfully disconnected.'))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.')
        )
        response.headers['Content-Type'] = 'application/json'
        return response


def remove_session():
    # the dictionary needs to be copied to avoid a runtime error
    sess = login_session.copy()
    for (key, value) in sess.items():
        del login_session[key]


# JSON APIs to view Todolist Information
@app.route('/todolist/<int:todolist_id>/list/JSON')
def todolist_list_json(todolist_id):
    items = session.query(ListItem).filter_by(
        todolist_id=todolist_id).all()
    if not items:
        return jsonify("No such todolist exists")
    return jsonify(ListItems=[i.serialize for i in items])


@app.route('/todolist/<int:todolist_id>/list/<int:list_id>/JSON')
def list_item_json(todolist_id, list_id):
    try:
        list_item = session.query(ListItem).filter_by(
            id=list_id, todolist_id=todolist_id
        ).one()
    except:
        return jsonify("No such list exists")
    return jsonify(List_Item=list_item.serialize)


@app.route('/todolist/JSON')
def todolists_json():
    todolists = session.query(Todolist).all()
    return jsonify(todolists=[r.serialize for r in todolists])


# Show all todolists
@app.route('/')
@app.route('/todolist/')
def show_todolists():
    todolists = session.query(Todolist).order_by(asc(Todolist.name))
    return render_template(
        'todolists.html',
        todolists=todolists,
        login_session=login_session
    )


# Create a new todolist


@app.route('/todolist/new/', methods=['GET', 'POST'])
@login_required
def new_todolist():
    if request.method == 'POST':
        new_todolist_obj = Todolist(
            name=request.form['name'],
            user_id=login_session['user_id']
        )
        session.add(new_todolist_obj)
        flash(
            'New Todolist %s Successfully Created' %
            new_todolist_obj.name
        )
        session.commit()
        return redirect(url_for('show_todolists'))
    else:
        return render_template('newTodolist.html')


# Edit a todolist


@app.route('/todolist/<int:todolist_id>/edit/', methods=['GET', 'POST'])
@login_required
def edit_todolist(todolist_id):
    try:
        edited_todolist = session.query(
            Todolist).filter_by(
            id=todolist_id
        ).one()
    except:
        return "No such todolist exists."
    if edited_todolist.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
               "alert('You are not authorized to edit this todolist. " \
               "Please create your own todolist in order to edit.');}" \
               "</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name'] != edited_todolist.name:
            edited_todolist.name = request.form['name']
            flash('Todolist Successfully Edited %s' % edited_todolist.name)
        return redirect(url_for('show_todolists'))
    else:
        return render_template(
            'editTodolist.html',
            todolist=edited_todolist
        )


# Delete a todolist
@app.route('/todolist/<int:todolist_id>/delete/', methods=['GET', 'POST'])
@login_required
def delete_todolist(todolist_id):
    try:
        todolist_to_delete = session.query(
            Todolist).filter_by(id=todolist_id).one()
    except:
        return "No such todolist to delete"
    if todolist_to_delete.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
               "alert('You are not authorized to delete this todolist. " \
               "Please create your own todolist in order to delete.');}" \
               "</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(todolist_to_delete)
        list_items_to_delete = session.query(ListItem).filter_by(
            todolist_id=todolist_id
        ).all()
        for del_list in list_items_to_delete:
            session.delete(del_list)
        flash('%s Successfully Deleted' % todolist_to_delete.name)
        session.commit()
        return redirect(
            url_for(
                'show_todolists',
                todolist_id=todolist_id
            )
        )
    else:
        return render_template(
            'deleteTodolist.html',
            todolist=todolist_to_delete
        )


# Show a todolist list


@app.route('/todolist/<int:todolist_id>/')
@app.route('/todolist/<int:todolist_id>/list/')
def show_list(todolist_id):
    try:
        todolist = session.query(Todolist).filter_by(
            id=todolist_id
        ).one()
    except:
        return "No such todolist"
    creator = get_user_info(todolist.user_id)
    if creator is None:
        return "The owner has shut down the todolist"
    items = session.query(ListItem).filter_by(
        todolist_id=todolist_id).all()
    return render_template(
        'list.html',
        items=items,
        todolist=todolist,
        creator=creator,
        login_session=login_session
    )


# Create a new list item
@app.route(
    '/todolist/<int:todolist_id>/list/new/',
    methods=['GET', 'POST']
)
@login_required
def new_list_item(todolist_id):
    try:
        todolist = session.query(Todolist).filter_by(
            id=todolist_id
        ).one()
    except:
        return "No such todolist"
    if login_session['user_id'] != todolist.user_id:
        return "<script>function myFunction() {" \
               "alert(" \
               "'You are not authorized to add list items " \
               "to this todolist. " \
               "Please create your own todolist in order to add items.');}" \
               "</script><body onload='myFunction()''>"
    if request.method == 'POST':
        new_item = ListItem(
            name=request.form['name'],
            description=request.form['description'],
            priority=request.form['priority'],
            todolist_id=todolist_id,
            user_id=todolist.user_id
        )
        session.add(new_item)
        session.commit()
        flash('%s Added to the List' % new_item.name)
        return redirect(url_for('show_list', todolist_id=todolist_id))
    else:
        return render_template('newlistitem.html', todolist_id=todolist_id)


# Edit a list item


@app.route(
    '/todolist/<int:todolist_id>/list/<int:list_id>/edit',
    methods=['GET', 'POST']
)
@login_required
def edit_list_item(todolist_id, list_id):
    try:
        edited_item = session.query(ListItem).filter_by(
            id=list_id
        ).one()
    except:
        return "No such item"
    try:
        todolist = session.query(Todolist).filter_by(
            id=todolist_id
        ).one()
    except:
        return "No such todolist"
    if login_session['user_id'] != todolist.user_id:
        return "<script>function myFunction() {" \
               "alert('You are not authorized to edit list items" \
               " to this todolist. " \
               "Please create your own todolist in order " \
               "to edit items.');}" \
               "</script><body onload='myFunction()''>"
    if request.method == 'POST':
        for (key, value) in request.form.items():
            setattr(edited_item, key, value)
        session.add(edited_item)
        session.commit()
        flash('List Item Successfully Edited')
        return redirect(url_for('show_list', todolist_id=todolist_id))
    else:
        return render_template(
            'editlistitem.html',
            todolist_id=todolist_id,
            list_id=list_id,
            item=edited_item
        )


# Delete a list item
@app.route(
    '/todolist/<int:todolist_id>/list/<int:list_id>/delete',
    methods=['GET', 'POST']
)
@login_required
def delete_list_item(todolist_id, list_id):
    try:
        todolist = session.query(Todolist).filter_by(
            id=todolist_id
        ).one()
    except:
        return "No such todolist"
    try:
        item_to_delete = session.query(ListItem).filter_by(
            id=list_id
        ).one()
    except:
        return "No such item"
    if login_session['user_id'] != todolist.user_id:
        return "<script>function myFunction() {" \
               "alert('You are not authorized to delete list items " \
               "to this todolist. " \
               "Please create your own todolist in order to delete " \
               "items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(item_to_delete)
        session.commit()
        flash('List Item Successfully Deleted')
        return redirect(url_for('show_list', todolist_id=todolist_id))
    else:
        return render_template('deleteListItem.html', item=item_to_delete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        remove_session()
        flash("You have successfully been logged out.")
        return redirect(url_for('show_todolists'))
    else:
        flash("You were not logged in")
        return redirect(url_for('show_todolists'))


if __name__ == '__main__':
    app.secret_key = main_app.get('secret_key', 'super_secret_key')
    app.debug = main_app.get('debug', True)
    app.config['SESSION_TYPE'] = main_app.get('session_type', 'filesystem')
    app.run(
        host=main_app.get('host', '0.0.0.0'),
        port=main_app.get('port', 5000)
    )


# View all todolists JSON
@app.route('/todolist/JSON')
def todolistsJSON():
    todolists = session.query(Todolist).all()
    return jsonify(todolists=[r.serialize for r in todolists])


# View all list items with todolist JSON
@app.route('/todolist/<int:todolist_id>/list/JSON')
def todolistListJSON(todolist_id):
    todolist = session.query(Todolist).filter_by(id=todolist_id).one()
    items = session.query(ListItem).filter_by(todolist_id=todolist_id).all()
    return jsonify(ListItems=[i.serialize for i in items])


# View specific details about list item JSON
@app.route('/todolist/<int:todolist_id>/list/<int:list_id>/JSON')
def listItemJSON(todolist_id, list_id):
    List_Item = session.query(ListItem).filter_by(id=list_id).one()
    return jsonify(List_Item=List_Item.serialize)
