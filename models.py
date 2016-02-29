import cnfg

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from instagram.client import InstagramAPI
from instagram.bind import InstagramAPIError

from db_setup import Base, User, Media, Follower

# Configuring the database connection.
engine = create_engine('sqlite:///instagram.sqlite')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()

# Configuring the instagram api client.
config = cnfg.load(".instagram_config")
api = InstagramAPI(client_id=config['CLIENT_ID'], 
				   client_secret=config['CLIENT_SECRET'])


def get_user_id(username):
	''' Given a username, return the instagram user_id.
		Only returns exact match. '''

	user_search = api.user_search(q=username)
	return user_search[0].id

def get_user_basics(user_id):
	''' Returns a dictionary with instagram user data
		stored for a given user_id. If the user's account
		is private this will return None.'''

	try:
		user = api.user(user_id = user_id)
		# Extract data and store in dict
		user_basics = {'user_id' : user_id}
		user_basics['username'] = user.username
		user_basics['bio'] = user.bio
		user_basics['num_followers']= user.counts['followed_by']
		user_basics['num_following'] = user.counts['follows']
		user_basics['num_posts'] = user.counts['media']

		return user_basics
	except InstagramAPIError:
		print 'This user is private'
		return None

def get_user_media(user_id):
	''' Given an instagram user id, this will pull the recent media
		(last 20) that the user has posted from the api and return this 
		data list of dictionaries with media content. If the user's account
		is private this will return None.
	'''

	try:
		media_list, next = api.user_recent_media(user_id = user_id)

		user_media_list = []
		for media in media_list:
			user_media = {'media_id' : media.id,
						  'num_likes' : media.like_count,
						  'num_comments' : media.comment_count,
						  'caption' : get_caption_text(media),
						  'latitude' : get_latitude(media),
						  'longitude' : get_longitude(media)}
			user_media_list.append(user_media)
		return user_media_list

	except InstagramAPIError:
		print 'This user is private'
		return None

def get_user_followers(user_id):
	''' Given an instagram user_id this will grab all of
		a user's followers and return them as a list. It will
		return None if the user is private.'''

	try:
		user_follower_list = []
		followers, next = api.user_followed_by(user_id=user_id)
		for follower in followers:
			user_follower_list.append(follower.id)
		while next:
			followers, next = api.user_followed_by(with_next_url=next)
			for follower in followers:
				user_follower_list.append(follower.id)
		return user_follower_list

	except InstagramAPIError:
		print 'This user is private'
		return None

##### Functions to store new information in the database. #####

def store_user(user_id,user_basics):
	'''Stores a user's basic information dict in the database.'''

	new_user = User(user_id=user_id,
					username=user_basics['user_id'],
					bio=user_basics['bio'],
					num_followers=user_basics['num_followers'],
					num_following=user_basics['num_following'],
					num_posts=user_basics['num_posts'])
	commit_to_db(new_user)

def store_media(user_id,user_media_list):
	'''Stores a user's media dict in the database.'''

	for media in user_media_list:
		new_media = Media(user_id=user_id,
						  media_id=media['media_id'],
						  num_likes=media['num_likes'],
						  num_comments=media['num_comments'],
						  caption=media['caption'],
						  latitude=media['latitude'],
						  longitude=media['longitude'])
		commit_to_db(new_media)

def store_followers(user_id,user_follower_list):
	''' A function that stores the user-follower relationship
		as a directed pair in the database.'''

	for user_id in user_follower_list:
		new_follower = Follower(user_id=user_id,follower_id=user_id)
		commit_to_db(new_follower)




##### Helper functions ######
def get_latitude(media_object):
	'''Exception handling for getting latitude.'''
	try:
		return media_object.location.point.latitude
	except AttributeError:
		return None

def get_longitude(media_object):
	'''Exception handling for getting longitude.'''
	try:

		return media_object.location.point.longitude
	except AttributeError:
		return None

def get_caption_text(media_object):
	'''Exception handling for getting caption.'''
	try:
		return media_object.caption.text
	except AttributeError:
		return None

def commit_to_db(new_object):
	'''Commiting new object to the database.'''
	try:
		session.add(new_object)
		session.commit()
		print "succesfully added object!"
	except:
		print "IntegrityError"
		session.rollback()
		# session.close()



##### Get an instagram user's list of follwers



key_username = 'eglum'
key_id = get_user_id(key_username)
m = get_user_media(key_id)
u = get_user_basics(key_id)
f = get_user_followers(key_id)
store_user(key_id,u)
store_media(key_id,m)
store_followers(key_id,f)