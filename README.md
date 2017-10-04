Item Catalog Application
========================

The Udacity Full Stack Developer Nanodegree -  Project 4 Item Catalog Application in the form of a To Do Application utilizing the following ideas/technologies:

- Flask/Jinja2 Templates
- CRUD functionality
- OAuth2 Login Authentication (Google)
- JSON Endpoints

## Getting Started

- Install dependencies (I recommend creating a python3 virtualenv)
```bash
pip install -r requirements.txt
```

- Rename the file <b>.env.example</b> to <b>.env</b>. You will need to replace the bold text noted below with your own Google OAuth2 credentials.
<pre>
google_client_id=<b>your_google_client_id</b>
google_project_id=<b>your_google_project_id</b>
google_client_secret=<b>your_google_client_secret</b>
</pre>

- Prepopulate the database (optional)
```bash
python database_populate.py
```

- Run the application
```bash
python project.py
```

- View the application in your browser<br>
[http://localhost:5000/](http://localhost:5000/)
or
[http://0.0.0.0:5000/](http://0.0.0.0:5000/)



## JSON Endpoints

View all lists
<pre>/todolist/JSON</pre>

View all list items in the current list
<pre>/todolist/<b><i>list_id</i></b>/list/JSON</pre>

View specific item
<pre>/todolist/<b><i>list_id></i></b>/list/<b>><i>list_item_id</i></b>/JSON</pre>


## Version

- Version 0.1
