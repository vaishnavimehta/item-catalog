#import files
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItems, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
session.rollback()

# this function is initiated whenever we click on log in button it renders login template and passes state which is actually a token.
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# this function is implemented when google sign in button is clicked.
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validates state token passed to login page.
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code.
    code = request.data

    try:
        # stores credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # validates access token.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # if error occurs passes 500 as status and aborts.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify access token.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # valdates access token for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    #if user already logged in then sends status as 200.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        flash("you are now logged in as %s" % login_session['user_id'])
        return response

    # Store credentials in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Store user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    #cheks if user is already in user database. If not it stores user info in User database.
    useremail=getUserID(login_session['email'])
    if not useremail:
        useremaail=createUser(login_session)
        login_session['user_id']=useremaail
    else:
        login_session['user_id']=useremail



    #Creates an output for user and sends successful state 200.
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 150px; height: 150px;border-radius: 100px;-webkit-border-radius: 100px;-moz-border-radius: 100px;margin-top:20px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done"
    response = make_response(json.dumps(output),
                                 200)
    response.headers['Content-Type'] = 'application/json'
    return response

# code to diconnect current user.
@app.route('/gdisconnect')
def gdisconnect():
        # if no user is logged in:
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print result
	#if  user is logged in:
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash("Successfully disconnected.")
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response = make_response(redirect(url_for('showLogin')))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # if given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Shows all restuarants if user is not logged in else shows restaurants created by the user.
@app.route('/')
@app.route('/restaurants')
def allrestaurants():
    items = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template('publicrestaurants.html', restaurants=items)
    else:
        items = session.query(Restaurant).filter_by(user_id=login_session['user_id'])
        return render_template('restaurant.html', items=items)

# Creating a new restaurant.
@app.route('/restaurants/new', methods=['GET', 'POST'])
def newRestaurant():
    # If user not logged in it redirects to login page.
    if 'username' not in login_session:
        flash("To create new restaurant first you have to login")
        return redirect('/login')
    # shows form to create new restaurant and validates the id given by user.
    if request.method == 'POST':
        id=int(request.form['id'])
        items = session.query(Restaurant).all()
        flag=0
        for i in items:
            if id == i.id:
                flag=1
                break
        if flag == 1:
            flash("id taken")
            return redirect(url_for('newRestaurant'))
        else:
            newItem = Restaurant(name=request.form['name'], id=id, user_id=login_session['user_id'])
            session.add(newItem)
            session.commit()
            flash("new menu item named "+newItem.name+" created!")
            return redirect(url_for('allrestaurants'))
    else:
        return render_template('newRestaurant.html')


# edits specific restaurant. if user not signed in redirects to login. if selected restaurant is not created by user, flashes error message and redirects to
# restraunt page. If restaurant id does not exists, flashes message and redirects. If none of above is true, edits current restaurnat name.
@app.route('/restaurants/<int:restaurant_id>/edit',
           methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    if 'username' not in login_session:
        flash("To edit restaurant first you have to login")
        return redirect('/login')
    output=''
    editedItem = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if editedItem == None:
        flash("incorrect restaurant id")
        return redirect(url_for('allrestaurants'))
    if editedItem.user_id != login_session['user_id']:
        flash("you are not authorised to edit this restaurant.It is not created by you") 
        return redirect(url_for('allrestaurants'))
    if request.method == 'POST':
        if request.form['name']:
            n=request.form['name']
            output+='Restaurant '
            output+= editedItem.name
            output+=' renamed to '
            output+=n
            editedItem.name = n
        session.add(editedItem)
        session.commit()
        flash(output)
        return redirect(url_for('allrestaurants'))
    else:
        return render_template(
            'editRestaurant.html', restaurant_id=restaurant_id, item=editedItem)

# Delete restaurant code. if user not signed in redirects to login. if selected restaurant is not created by user, flashes error message and redirects to
# restraunt page. If restaurant id does not exists, flashes message and redirects. If none of above is true, deletes current restaurant and its menu items.
@app.route('/restaurants/<int:restaurant_id>/delete',
           methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    if 'username' not in login_session:
        flash("To delete restaurant first you have to login")
        return redirect('/login')
    delItem = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if delItem == None:
        flash("incorrect restaurant id")
        return redirect(url_for('allrestaurants'))
    if delItem.user_id != login_session['user_id']:
        flash("you are not authorised to delete this restaurant.It is not created by you") 
        return redirect(url_for('allrestaurants'))
    if request.method == 'POST':
        session.delete(delItem)
        session.commit()
        itemToDelete = session.query(MenuItems).filter_by(restaurant_id=restaurant_id).all()
        for i in itemToDelete:
            session.delete(i)
            session.commit()
        flash("Restaurant "+delItem.name+" deleted")
        return redirect(url_for('allrestaurants'))
    else:
        return render_template('deleteRestaurant.html', item=delItem)

# It returns JSON endpoint of restaurants.
@app.route('/restaurants/JSON')
def restaurantJSON():
    items = session.query(Restaurant).all()
    return jsonify(Restaurant=[i.ser for i in items])

# It returns JSON endpoint of users.
@app.route('/user/JSON')
def userJSON():
    items = session.query(User).all()
    return jsonify(User=[i.ser for i in items])

# It returns JSON endpoint of menu of specific restaurant.
@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("incorrect restaurant id")
        return redirect(url_for('allrestaurants'))
    items = session.query(MenuItems).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

# It returns JSON endpoint of specific menu item of specific restaurant.
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def restaurantMenuspecificJSON(restaurant_id,menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("incorrect restaurant id")
        return redirect(url_for('allrestaurants'))
    items = session.query(MenuItems).filter_by(id=menu_id).first()
    if items == None:
        flash("incorrect menu id")
        return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
    return jsonify(MenuItems=[items.serialize])


#shows menu of specific restaurant.
@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("incorrect restaurant id")
        return redirect(url_for('allrestaurants'))
    creator = getUserInfo(restaurant.user_id)
    items = session.query(MenuItems).filter_by(restaurant_id=restaurant_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicmenu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id, creator=creator)
    else:
        return render_template('menu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id, creator=creator)

# Creates new menu Item. If user not logged in redirects to restaurant menu page. 
@app.route('/restaurants/<int:restaurant_id>/new', methods=['GET', 'POST'])
def newMenuItems(restaurant_id):
    if 'username' not in login_session:
        flash("To create new restaurant first you have to login")
        return redirect('/login')
    if request.method == 'POST':
        newItem = MenuItems(name=request.form['name'], description=request.form[
                           'description'], price=request.form['price'], course=request.form['course'], restaurant_id=restaurant_id,  user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("new menu item named "+newItem.name+" created!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)

# Edits specific menu Item.
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/edit',
           methods=['GET', 'POST'])
def editMenuItems(restaurant_id, menu_id):
    if 'username' not in login_session:
        flash("To create new restaurant first you have to login")
        return redirect('/login')
    output=''
    editedItem = session.query(MenuItems).filter_by(id=menu_id).first()
    if editedItem == None:
        flash("incorrect menu id")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if editedItem.restaurant_id != restaurant_id:
        flash("incorrect restaurant and menu id combination")
        return redirect(url_for('allrestaurants'))
    if editedItem.user_id != login_session['user_id']:
        flash("you are not authorised to edit this item.It is not created by you") 
        return redirect(url_for('restaurantMenu'))

    if request.method == 'POST':
        if request.form['name']:
            n=request.form['name']
            output+='menu item '
            output+= editedItem.name
            output+=' renamed to '
            output+=n
            editedItem.name = n
        session.add(editedItem)
        session.commit()
        flash(output)
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)


# deletes specific menu Item.
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/delete',
           methods=['GET', 'POST'])
def deleteMenuItems(restaurant_id, menu_id):
    if 'username' not in login_session:
        flash("To create new restaurant first you have to login")
        return redirect('/login')
    itemToDelete = session.query(MenuItems).filter_by(id=menu_id).first()
    if itemToDelete == None:
        flash("incorrect menu id")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if itemToDelete.restaurant_id != restaurant_id:
        flash("incorrect restaurant and menu id combination")
        return redirect(url_for('allrestaurants'))
    if itemToDelete.user_id != login_session['user_id']:
        flash("you are not authorised to delete this item.It is not created by you") 
        return redirect(url_for('restaurantMenu'))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("menu item "+itemToDelete.name+" deleted")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteconfirmation.html', item=itemToDelete)

# Creates new user and adds data to User database.
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

# if user logged in, returns tuuple containing user data else redirects.
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    if user == None:
        flash("unauthorised user")
        return redirect(url_for('allrestaurants'))
    return user

# returns id of user.
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)