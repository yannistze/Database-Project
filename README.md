# Database Project

"New York City Museums, Event Recommendation Application using Flask"

**Description:**

Based on user's interaction with the database, the Application displays available events of Museums in New York City. The user's interactions comprise of the creation and update of a personal profile, the ability to add or remove friends that also utilize the Application, as well as the flexibility of following specific Museums of New York City that much each person's preferences.

## Install Required Packages

Install pip if needed

        sudo apt-get install python-pip

Install libraries

        pip install click flask sqlalchemy


## Locate and excecute `server.py` file inside webserver folder

Edit `server.py` to set your database URI

        DATABASEURI = "<database uri>"


Run it in the shell

        python server.py

Get help:

        python server.py --help
