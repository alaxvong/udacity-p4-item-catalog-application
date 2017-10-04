from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Todolist, Base, ListItem, User

engine = create_engine('sqlite:///todolistwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
User1 = User(name="Tim", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

User2 = User(name="Alax", email="alaxdesigns@gmail.com",
             picture='https://avatars3.githubusercontent.com/u/9137752?v=4&s=460')
session.add(User2)
session.commit()

# Create Todo Lists
todolist1 = Todolist(user_id=1, name="Work")

session.add(todolist1)
session.commit()

todolist2 = Todolist(user_id=2, name="Necessities")

session.add(todolist2)
session.commit()

# Create Lists Items
listItem1 = ListItem(
    user_id=1,
    name="File monthly report",
    description="Due 10/7",
    priority="HighPriority",
    todolist=todolist1)

session.add(listItem1)
session.commit()

listItem2 = ListItem(
    user_id=1,
    name="Cornhole Tournament",
    description="Due 11/10",
    priority="MedPriority",
    todolist=todolist1)

session.add(listItem2)
session.commit()

listItem3 = ListItem(
    user_id=1,
    name="Water Plant",
    description="Every 4 days",
    priority="LowPriority",
    todolist=todolist1)

session.add(listItem3)
session.commit()

listItem4 = ListItem(
    user_id=2,
    name="Feed the cat",
    description="The cat's hungry.",
    priority="HighPriority",
    todolist=todolist2)

session.add(listItem4)
session.commit()

listItem5 = ListItem(
    user_id=2,
    name="Pay Bills",
    description="Credit Card, Phone and Electricity.",
    priority="LowPriority",
    todolist=todolist2)

session.add(listItem5)
session.commit()

listItem6 = ListItem(
    user_id=2,
    name="Work Out",
    description="Preferably soon",
    priority="LowPriority",
    todolist=todolist2)

session.add(listItem6)
session.commit()

print("Database populated")