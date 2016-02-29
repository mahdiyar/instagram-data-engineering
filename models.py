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
		basics = {'user_id' : user_id}
		basics['username'] = user.username
		basics['bio'] = user.bio
		basics['followers_count']= user.counts['followed_by']
		basics['follows_count'] = user.counts['follows']
		basics['media_count'] = user.counts['media']

		return basics
	except InstagramAPIError:
		print 'This user is private'
		return None

def get_user_media(user_id):
	''' Given an instagram user id, this will pull the recent media
		(last 10) that the user has posted from the api and return this 
		data in a dictionary with media id as the key. If the user's account
		is private this will return None.
	'''

	try:
		media_list, next = api.user_recent_media(user_id = user_id)

		media_data = {}
		for media in media_list:
			media_data[media.id] = {'likes_count' : media.like_count,
									'comments_count' : media.comment_count,
									'latitude' : get_latitude(media),
									'longitude' : get_longitude(media),
									'caption' : get_caption_text(media)}
		return media_data

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

def store_followers(user_id,user_follower_list):

	for user_id in user_follower_list:
		new_follower = Follower(user_id=user_id,follower_id=user_id)
		commit(new_follower)




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

def commit(new_object):
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
followers = get_user_followers(key_id)
store_followers(key_id,followers)