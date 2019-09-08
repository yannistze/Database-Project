"""
Go to http://localhost:8111 in your browser
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session
from string import punctuation
from datetime import datetime
import hashlib

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = b'<secret_key>'



DB_USER = "<username>"
DB_PASSWORD = "<password>"

DB_SERVER = "<server URL>"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass

#########
# INDEX #
#########

@app.route('/')
def index():

  # if logged in already, redirect to welcome page
  if 'u_id' in session:
  	return redirect('/welcome')
  # else return index page
  return render_template('index.html')

###########
# SIGN-UP #
###########

@app.route('/signup', methods=['POST', 'GET'])
def signup():
	alpha = ['a','b','c','d','e',
			 'f','g','h','i','j',
			 'k','l','m','n','o',
			 'p','q','r','s','t',
			 'u','v','x','y','z']
	number = ['1','2','3','4','5',
			  '6','7','8','9','0']
	index_length = False
	index_punctuation = False
	index_numeric = False
	index_alpha = False
	index_upper_alpha = False

	# if request is get it returns the signup page
	if request.method == 'GET':
		return render_template('signup.html')
	# else it submits the signup request and redirects you accordingly
	elif request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		dob = request.form['dob']
		description = request.form['description']
		password = request.form['password']
		confirm_password = request.form['confirmpassword']

		if len(password) >= 8 & len(password) < 128:
			index_length = True
			for item in password:
				if item in list(punctuation):
					index_punctuation = True
					continue
				if item in number:
					index_numeric = True
					continue
				if item in alpha:
					index_alpha = True
					continue
				if item in [x.upper() for x in alpha]:
					index_upper_alpha = True
					continue

		if index_length & index_punctuation & index_numeric & index_alpha & index_upper_alpha:
			if password == confirm_password:
				password = hashlib.sha1(password.encode('utf8')).hexdigest()

				cmd = """INSERT INTO users(email, name, dob, description, password) 
						 VALUES (:email, :name, :dob, :description, :pw)"""

				try: 
					g.conn.execute(text(cmd), name = name, email=email, 
						dob=dob, description=description, pw=password);
					return redirect('/')
				except:
					pass
			else:
				return redirect('/signup')
		else:
			return redirect('/signup')

#########
# LOGIN #
#########

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		password = hashlib.sha1(password.encode('utf8')).hexdigest()

		cmd = """SELECT u_id
				 FROM users
				 WHERE email = :email AND password = :pw
			  """

		cursor = g.conn.execute(text(cmd), email=str(email), pw=str(password))
		try:
			u_id = cursor.fetchone()['u_id']
			cursor.close()
			if u_id:
				session['u_id'] = u_id
				return redirect('/welcome')
			else:
				return redirect('/')
		except TypeError:
			return redirect('/')
	return render_template('index.html')

##########
# LOGOUT #
##########

@app.route('/logout', methods=['POST'])
def logout():
	if request.method == 'POST':
		session.pop('u_id', None)
		return render_template('index.html')

###########
# WELCOME #
###########

@app.route('/welcome')
def welcome():

	cmd = """
			SELECT *
			FROM users
			WHERE u_id = :u_id
		  """

	cursor = g.conn.execute(text(cmd), u_id=session['u_id'])
	record = cursor.fetchone()
	cursor.close()

	context = dict(data=record)

	return render_template("welcome.html", **context)

############
# NOTEBOOK #
############

@app.route('/notebook', methods=['POST', 'GET'])
def notebook():
	if request.method == 'GET':

		cmd = """
				SELECT *
				FROM entries
				WHERE u_id = :u_id
				ORDER BY entry_date DESC
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'])
		_ = []
		for result in cursor:
			_.append(result)
		cursor.close()

		context = dict(data=_)

		return render_template("notebook.html", **context)

	# otherwise it's a new entry
	else:
		entry_text = request.form['entry_text']
		title = request.form['title']
		entry_date = str(datetime.now())
		cmd = """INSERT INTO entries(entry_text, title, entry_date, u_id) 
				 VALUES (:entry_text, :title, :entry_date, :u_id)""";
		try: 
			g.conn.execute(text(cmd), entry_text = entry_text, title=title, 
										 entry_date=entry_date, u_id=session['u_id']);
			return redirect('/notebook')
		except:
			pass

###########
# MUSEUMS #
###########
@app.route('/museums')
def museums():

	# favorite museums
	cmd = """
			SELECT *
			FROM museums
			WHERE museum_id IN (SELECT museum_id
								FROM favorite
								WHERE favorite.u_id = :u_id)
		  """
	cursor = g.conn.execute(text(cmd), u_id=session['u_id'])
	favs = []
	for result in cursor:
		favs.append(result)
	cursor.close()

	# other museums
	cmd = """
			SELECT *
			FROM museums
			WHERE museum_id NOT IN (SELECT museum_id
									FROM favorite
									WHERE favorite.u_id = :u_id)
		  """
	cursor = g.conn.execute(text(cmd), u_id=session['u_id'])
	others = []
	for result in cursor:
		others.append(result)
	cursor.close()

	context = dict(favs=favs, others=others)
	return render_template("museums.html", **context)

###################
# SPECIFIC MUSEUM #
###################

@app.route('/museum', methods=['POST', 'GET'])
def museum():
	if request.method == 'POST':
		try:

			museum_name = request.form['name']


			# get the museum data
			cmd = """
					SELECT *
					FROM museums
					WHERE name = :name
				  """
			cursor = g.conn.execute(text(cmd), name=museum_name)
			data = cursor.fetchone()
			cursor.close()

			mid = data['museum_id']
		except:
			mid = request.form['m_id']

			cmd = """
					SELECT *
					FROM museums
					WHERE museum_id = :mid
				  """
			cursor = g.conn.execute(text(cmd), mid=mid)
			data = cursor.fetchone()
			cursor.close()

		session['mid'] = mid

	else:
		cmd = """
				SELECT *
				FROM museums
				WHERE museum_id = :mid
			  """
		cursor = g.conn.execute(text(cmd), mid=session['mid'])
		data = cursor.fetchone()
		cursor.close()
			
	# check if the user follows that museum
	cmd = """
			SELECT *
			FROM favorite
			WHERE u_id = :u_id
			AND museum_id = :m_id
		  """
	cursor = g.conn.execute(text(cmd), u_id=session['u_id'], m_id=session['mid'])
	record = cursor.fetchone()
	cursor.close()
	if record:
		rel = 'Unfavorite'
	else:
		rel = 'Favorite'

	
	# find upcoming events for that museum
	date = datetime.now()
	cmd = """
			SELECT *
			FROM events
			WHERE museum_id = :m_id
			AND event_date >= DATE :event_date
			ORDER BY event_date ASC
			LIMIT 3
		  """
	cursor = g.conn.execute(text(cmd), m_id=session['mid'], event_date=date)

	events = []
	for record in cursor:
		events.append(record)
	cursor.close()



	context = dict(data=data, fav=rel, events=events)
	return render_template("museum.html", **context)

############
# FAVORITE #
############

@app.route('/favorite', methods=['POST'])
def favorite():
	if request.method == 'POST':
		mid = session['mid']

		# if user doesn't follow already then follow, else unfollow
		cmd = """
				SELECT *
				FROM favorite
				WHERE u_id = :u_id
				AND museum_id = :m_id
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'], m_id=mid)
		record = cursor.fetchone()
		cursor.close()

		if not record:
			cmd = """
					INSERT INTO favorite(u_id, museum_id)
					VALUES(:u_id, :museum_id)
				  """
			g.conn.execute(text(cmd), u_id=session['u_id'], museum_id=mid);

			return redirect('/museum')
		else:
			cmd = """
					DELETE FROM favorite
					WHERE u_id = :u_id AND museum_id = :museum_id

				  """
			g.conn.execute(text(cmd), u_id=session['u_id'], museum_id=mid);

			return redirect('/museum')



###########
# PROFILE #
###########

@app.route('/profile', methods=['GET', 'POST'])
def profile():
	if request.method == 'GET':

		# fetch user data
		cmd = """
				SELECT *
				FROM users
				WHERE u_id = :u_id
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'])
		data = cursor.fetchone()
		cursor.close()

		context = dict(data=data)
		return render_template("profile.html", **context)

	# user submits a change to their profile
	else:
		desc = request.form['description']

		cmd = """
				UPDATE users
				SET description = :description
				WHERE u_id = :u_id
			  """

		g.conn.execute(text(cmd), description=desc, u_id=session['u_id'])

		return redirect('/profile')

#########
# USERS #
#########

@app.route('/userbase', methods=['GET', 'POST'])
def userbase():
	if request.method == 'GET':
		cmd = """
				SELECT *
				FROM users
				WHERE u_id IN (SELECT followee_id
							   FROM follow
							   WHERE follower_id = :fid)
			  """
		cursor = g.conn.execute(text(cmd), fid=session['u_id'])
		following = []
		for record in cursor:
			following.append(record) 
		cursor.close()

		cmd = """
				SELECT *
				FROM users
				WHERE u_id NOT IN (SELECT followee_id
								   FROM follow
								   WHERE follower_id = :fid)
				AND u_id != :u_id
		      """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'], fid=session['u_id'])
		other_users = []
		for record in cursor:
			other_users.append(record) 
		cursor.close()

		context = dict(data_f=following, data_u=other_users)
		return render_template("userbase.html", **context)

	# if post method
	else:
		f_email = request.form['f_email']
		# use the email to find that user's id
		cmd = """
				SELECT u_id
				FROM users
				WHERE email = :email
			  """
		cursor = g.conn.execute(text(cmd), email=f_email)
		f_id = cursor.fetchone()['u_id']
		cursor.close()

		# check if user is following user
		cmd = """
				SELECT *
				FROM follow
				WHERE follower_id = :fid1
				AND followee_id = :fid2
			  """
		cursor = g.conn.execute(text(cmd), fid1=session['u_id'], fid2=f_id)
		record = cursor.fetchone()
		cursor.close()

		# if not following, follow
		if not record:
			cmd = """
					INSERT INTO follow(follower_id, followee_id)
					VALUES (:fid1, :fid2)
				  """
			g.conn.execute(text(cmd), fid1=session['u_id'], fid2=f_id)

			return redirect('/userbase')

		# if following, unfollow
		else:
			cmd = """
					DELETE FROM follow
					WHERE follower_id = :fid1 AND followee_id = :fid2
				  """
			g.conn.execute(text(cmd), fid1=session['u_id'], fid2=f_id)

			return redirect('/userbase')

##########
# EVENTS #
##########

@app.route('/events', methods=['GET', 'POST'])
def events():

	if request.method == 'GET':

		date = datetime.now()

		# attending events ordered DESC
		cmd = """
				SELECT *
				FROM events
				WHERE event_id IN (SELECT event_id
								   FROM attend
								   WHERE u_id = :u_id)
				AND event_date >= DATE :e_date
				ORDER BY event_date DESC
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'], e_date=date)

		favs = []
		for result in cursor:
			favs.append(result)
		cursor.close()

		# get upcoming events
		cmd = """
				SELECT *
				FROM events
				WHERE event_date >= DATE :e_date
				ORDER BY event_date DESC
			  """
		cursor = g.conn.execute(text(cmd), e_date=date)
		upcoming = []
		for result in cursor:
			upcoming.append(result)
		cursor.close()


		# get past events
		cmd = """
				SELECT *
				FROM events
				WHERE event_id NOT IN (SELECT event_id
									   FROM attend
									   WHERE u_id = :u_id)
				AND event_date < DATE :e_date
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'], e_date=date)
		past = []
		for result in cursor:
			past.append(result)
		cursor.close()


		context = dict(favs=favs, others=upcoming, past=past)
		return render_template("events.html", **context)

	else: # if post

		if request.form.get('e_id', False):
			e_id = request.form['e_id']

			# check if event exists
			cmd = """
					SELECT event_id
					FROM events
					WHERE event_id = :e_id
				  """
			cursor = g.conn.execute(text(cmd), e_id=e_id)
			record = cursor.fetchone()
			cursor.close()

			# if it exists direct to event page
			if record:
				session['e_id'] = request.form['e_id']
				return redirect('/event')

			# else return back to events page
			else:
				return redirect('/events')

		elif request.form.get('category', False):
			e_category = request.form['category']
			cat = e_category
			e_category = '%' + e_category.lower() + '%'

			# check if event exists
			cmd = """
					SELECT *
					FROM events
					WHERE lower(category) LIKE :e_category 
				  """
			cursor = g.conn.execute(text(cmd), e_category=e_category)
			category = []
			for result in cursor:
				category.append(result)
			cursor.close()

			context = dict(e_category=cat.upper(), category=category)
			return render_template("category.html", **context)

#########
# EVENT #
#########

@app.route('/event', methods=['GET', 'POST'])
def event():
	if request.method == 'GET':

		# get event info
		cmd = """
				SELECT *
				FROM events
				WHERE event_id = :e_id
			  """
		cursor = g.conn.execute(text(cmd), e_id=session['e_id'])
		event = cursor.fetchone()
		cursor.close()

		# get attending friends
		cmd = """
				SELECT *
				FROM users
				WHERE u_id IN (SELECT u_id
							   FROM attend
							   WHERE u_id IN (SELECT followee_id
							   				  FROM follow
							   				  WHERE follower_id = :fid)
							   AND event_id = :e_id)
			  """
		cursor = g.conn.execute(text(cmd), fid=session['u_id'], e_id=session['e_id'])
		att_friends = []
		for record in cursor:
			att_friends.append(record)
		cursor.close()

		# check if user is already attending
		cmd = """
				SELECT u_id
				FROM attend
				WHERE u_id = :u_id AND event_id = :e_id
			  """
		cursor = g.conn.execute(text(cmd), u_id=session['u_id'], e_id=session['e_id'])
		att = cursor.fetchone()
		cursor.close()
		print(att)

		if att:
			rel = 'Unattend'
		else:
			rel = ' Attend'
		
		# get posts
		cmd = """
				SELECT *
				FROM posts
				WHERE event_id = :e_id
			  """
		cursor = g.conn.execute(text(cmd), e_id=session['e_id'])

		posts = []
		for _ in cursor:
			posts.append(_)
		cursor.close()

		context = dict(event=event, friends=att_friends, att=rel, posts=posts)
		return render_template('event.html', **context)

	else:
		att_value = request.form['att_value']
		if att_value == 'Attend': # add attendance
			cmd = """
					INSERT INTO attend(u_id, event_id)
					VALUES (:u_id, :e_id)
				  """
			g.conn.execute(text(cmd), u_id=session['u_id'], e_id=session['e_id'])
			return redirect('/event')
		else: # remove attendance
			cmd = """
					DELETE FROM attend
					WHERE u_id = :u_id
					AND event_id = :e_id
				  """
			g.conn.execute(text(cmd), u_id=session['u_id'], e_id=session['e_id'])
			return redirect('/event')

#############
# MAKE POST #
#############
@app.route('/post', methods=['POST'])
def post():

	e_id = session['e_id']
	u_id = session['u_id']
	title = request.form['title']
	rating = request.form['rating']
	post_text = request.form['post_text']
	post_date = str(datetime.now())


	cmd = """
			INSERT INTO posts(u_id, post_text, title, rating, post_date, event_id)
			VALUES (:u_id, :post_text, :title, :rating, :post_date, :event_id)
		  """
	cursor = g.conn.execute(text(cmd), u_id=u_id, post_text=post_text, title=title,
							rating=rating, post_date=post_date, event_id=e_id)
	cursor.close()

	return redirect('/event')



if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
