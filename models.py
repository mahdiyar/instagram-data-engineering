import math
import cnfg

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from instagram.client import InstagramAPI
from instagram.bind import InstagramAPIError

from db_setup import Base, InstagramUser, Media, Follower

# Configuring the database connection.
engine = create_engine('postgresql://localhost/metis_adsthetic')
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
	return str(user_search[0].id)

def rate_limit_check():
	''' Given a username, return the instagram user_id.
		Only returns exact match. '''

	user_search = api.user_search(q='instagram')
	remaining_calls = int(api.x_ratelimit_remaining)

	return remaining_calls


def commit_to_db(new_object):
	'''Commiting new object to the database.'''

	try:
		session.add(new_object)
		session.commit()
		print "succesfully added object!"
	except IntegrityError:
		print "IntegrityError"
		session.rollback()
		# session.close()


######## Classes to pull user information from Instagram ########
class AddUserProfile():
	'''This class takes a instagram_id and grabs a user's profile information
	   stores it in the database.'''

	def __init__(self,instagram_id):
		self._instagram_id = instagram_id
		# Grab and store a user's basic profile data.
		basics, rate = self._get_user_profile()
		print rate
		self._store_user(basics)

	def _get_user_profile(self):
		''' Returns a tuple including a dictionary with instagram user data
			stored for a given user_id and the remaining amount of calls
			available to make on the api. If the user's account
			is private this will return (None, None).'''

		try:
			instagram_user = api.user(user_id = self._instagram_id)
			remaining_calls = int(api.x_ratelimit_remaining)
			# Extract data and store in dict
			instagram_user_profile = {'instagram_id' : self._instagram_id}
			instagram_user_profile['instagram_username'] = instagram_user.instagram_username
			instagram_user_profile['bio'] = instagram_user.bio
			instagram_user_profile['num_followers']= instagram_user.counts['followed_by']
			instagram_user_profile['num_following'] = instagram_user.counts['follows']
			instagram_user_profile['num_posts'] = instagram_user.counts['media']

			return instagram_user_profile, remaining_calls
		except InstagramAPIError:
			print 'This user is private'
			return None, None

	def _store_user(self,instagram_user_profile):
		'''Stores a user's basic information dict in the database.'''
		
		if instagram_user_profile:
			new_user = InstagramUser(instagram_id=self._user_id,
							instagram_username=instagram_user_profile['username'],
							bio=instagram_user_profile['bio'],
							num_followers=instagram_user_profile['num_followers'],
							num_following=instagram_user_profile['num_following'],
							num_posts=instagram_user_profile['num_posts'])
			commit_to_db(new_user)


class AddUserMedia():
	''' This class takes an instagram_id and grabs the user's recent media
		and stores all of this information in the database.'''

	def __init__(self,instagram_id,max_media=10):
		self._instagram_id = instagram_id
		self._max_media = float(max_media)

		# Grab and store a user's recent media data.
		media, _ = self._get_user_media()
		self._store_media(media)


	def _get_user_media(self):
		''' Given an instagram user id, this return a tuple including a list 
			of dictionaries containing data on the user's recent media and 
			the amount of remaining calls available to make on the api. If 
			the user's account is private this will return (None, None).
		'''

		try:
			media_list, next = api.user_recent_media(user_id = self._instagram_id)
			remaining_calls = int(api.x_ratelimit_remaining)
			user_media_list = []
			for media in media_list:
				user_media = {'media_id' : media.id,
							  'num_likes' : media.like_count,
							  'num_comments' : media.comment_count,
							  'caption' : self._get_caption_text(media),
							  'latitude' : self._get_latitude(media),
							  'longitude' : self._get_longitude(media)}
				user_media_list.append(user_media)
			return user_media_list, remaining_calls

		except InstagramAPIError:
			print 'This user is private'
			return None, None

	def _store_media(self,user_media_list):
		'''Stores a user's media dict in the database.'''

		if user_media_list:
			for media in user_media_list:
				new_media = Media(instagram_id=self._instagram_id,
								  media_id=media['media_id'],
								  num_likes=media['num_likes'],
								  num_comments=media['num_comments'],
								  caption=media['caption'],
								  latitude=media['latitude'],
								  longitude=media['longitude'])
				commit_to_db(new_media)

	##### Helper functions ######
	def _get_latitude(self,media_object):
		'''Exception handling for getting latitude.'''
		try:
			return media_object.location.point.latitude
		except AttributeError:
			return None

	def _get_longitude(self,media_object):
		'''Exception handling for getting longitude.'''
		try:
			return media_object.location.point.longitude
		except AttributeError:
			return None

	def _get_caption_text(self,media_object):
		'''Exception handling for getting caption.'''
		try:
			return media_object.caption.text
		except AttributeError:
			return None


class AddUserFollowers():
	'''This class takes an instagram_id and grabs the users follower data,
		and stores this information in the database.'''

	def __init__(self,instagram_id,max_followers=10000):
		self._instagram_id = instagram_id
		self._max_followers = float(max_followers)

		# Grab and store a user's list of followers.
		followers, remaining_calls = self._get_user_followers()
		print remaining_calls
		self._store_followers(followers)

	def _get_user_followers(self):
		''' Given an instagram_id this will return a tuple containing
			a list of the user's followers and the amount of remaining calls
			available to make on the api. If the user is private it will
			return (None, None).'''

		try:
			user_follower_list = []
			followers, next = api.user_followed_by(user_id=self._instagram_id)
			remaining_calls = int(api.x_ratelimit_remaining)
			for follower in followers:
				user_follower_list.append(follower.id)
			while next:
				followers, next = api.user_followed_by(with_next_url=next)
				remaining_calls = int(api.x_ratelimit_remaining)
				print remaining_calls
				for follower in followers:
					user_follower_list.append(follower.id)
			return user_follower_list, remaining_calls

		except InstagramAPIError:
			print 'This user is private'
			return None, None

	def _store_followers(self,user_follower_list):
		''' A function that stores the user-follower relationship
			as a directed pair in the database.'''

		if user_follower_list:
			for follower_id in user_follower_list:
				new_follower = Follower(instagram_id=self._instagram_id,follower_id=follower_id)
				commit_to_db(new_follower)


