# Item Catalog
Udacity Project

#Introduction :
1. This application provides a list of restaurants and their menus.
2. It uses google for authentication and authorisation.
3. A local permission system has also been implemented to keep users from changing other user's data.
4. If user is not logged in then he/she can only view restaurants and their menus.
5. If a user is logged in he/she can view, create, edit and delete restaurants and menu Items.
6. If a user is not logged in and still tries to edit, create or delete he/she is automatically redirected to login page.

#Software Requirements :
1. vagrant VM
2. Python 2.7
3. Flask 0.12.2
4. SQLAlchemy 1.1.10(which is already installed in case of vagrant)

#Files Description :
1. database_setup.py : Python file containing code for project's database.
2. restaurantmenuwithusers.sql : sql file created when above mentioned python file is run.
3. lotsofusers.py : file containing data to populate our database.
4. finalproject.py : main python file containing CRUD, authentication and authorisation functions.
5. client_secrets.json : a json file necessary for google authorisation.
6. templates : contains all HTML templates.
7. static : contains all css files.
8. README.md : has all the details of project.

# Setup : 
1. Go to directory that contains the project and launch vagrant VM.
2. Run commands 'vagrant up', 'vagrant ssh', 'cd /vagrant'.
3. Load the database by running 'python database_setup.py'.
4. Run command 'python lotsofusers.py'.
5. Run command 'python final_project.py'.
6. open 'localhost:5000/' or 'localhost:5000/restaurants' to test the application

# JSON endpoints : 
1. open 'localhost:5000/restaurants/JSON' to list all restaurants with their name and ID.
2. open 'localhost:5000/user/JSON' to list all users with their name and ID.
3. open 'localhost:5000/restaurants/<int:restaurant_id>/menu/JSON' and replace <int:restaurant_id> with a valid restaurant id to list all items of that restaurant with their name, ID, course, price and description.
4. open 'localhost:5000/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON' and replace <int:restaurant_id>,<int:menu_id> with a valid restaurant id and menu_id respectively to list specific item of specific restaurant with it's name, ID, course, price and description.

# Credits : 
This complete project is based on udacity videos and codes from videos and instructor notes.
