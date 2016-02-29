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


class AddFullUserData():
	'''This class takes a user_id and grabs the users profile information,
		recent media, and entire list of followers and stores all of this 
		information in the database.'''

	def __init__(self,user_id):
		self._user_id = user_id
		# Grab and store a user's basic profile data.
		basics = self._get_user_basics()
		self._store_user(basics)
		# Grab and store a user's recent media data.
		media = self._get_user_media()
		self._store_media(media)
		# Grab and store a user's list of followers.
		followers = self._get_user_followers()
		self._store_followers(followers)


	def _get_user_basics(self):
		''' Returns a dictionary with instagram user data
			stored for a given user_id. If the user's account
			is private this will return None.'''

		try:
			user = api.user(user_id = self._user_id)
			# Extract data and store in dict
			user_basics = {'user_id' : user.id}
			user_basics['username'] = user.username
			user_basics['bio'] = user.bio
			user_basics['num_followers']= user.counts['followed_by']
			user_basics['num_following'] = user.counts['follows']
			user_basics['num_posts'] = user.counts['media']

			return user_basics
		except InstagramAPIError:
			print 'This user is private'
			return None

	def _get_user_media(self):
		''' Given an instagram user id, this will pull the recent media
			(last 20) that the user has posted from the api and return this 
			data list of dictionaries with media content. If the user's account
			is private this will return None.
		'''

		try:
			media_list, next = api.user_recent_media(user_id = self._user_id)

			user_media_list = []
			for media in media_list:
				user_media = {'media_id' : media.id,
							  'num_likes' : media.like_count,
							  'num_comments' : media.comment_count,
							  'caption' : self._get_caption_text(media),
							  'latitude' : self._get_latitude(media),
							  'longitude' : self._get_longitude(media)}
				user_media_list.append(user_media)
			return user_media_list

		except InstagramAPIError:
			print 'This user is private'
			return None

	def _get_user_followers(self):
		''' Given an instagram user_id this will grab all of
			a user's followers and return them as a list. It will
			return None if the user is private.'''

		try:
			user_follower_list = []
			followers, next = api.user_followed_by(user_id=self._user_id)
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

	def _store_user(self,user_basics):
		'''Stores a user's basic information dict in the database.'''
		
		if user_basics:
			new_user = User(user_id=self._user_id,
							username=user_basics['user_id'],
							bio=user_basics['bio'],
							num_followers=user_basics['num_followers'],
							num_following=user_basics['num_following'],
							num_posts=user_basics['num_posts'])
			self._commit_to_db(new_user)

	def _store_media(self,user_media_list):
		'''Stores a user's media dict in the database.'''

		if user_media_list:
			for media in user_media_list:
				new_media = Media(user_id=self._user_id,
								  media_id=media['media_id'],
								  num_likes=media['num_likes'],
								  num_comments=media['num_comments'],
								  caption=media['caption'],
								  latitude=media['latitude'],
								  longitude=media['longitude'])
				self._commit_to_db(new_media)

	def _store_followers(self,user_follower_list):
		''' A function that stores the user-follower relationship
			as a directed pair in the database.'''

		if user_follower_list:
			for follower_id in user_follower_list:
				new_follower = Follower(user_id=self._user_id,follower_id=follower_id)
				self._commit_to_db(new_follower)




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

	def _commit_to_db(self,new_object):
		'''Commiting new object to the database.'''
		try:
			session.add(new_object)
			session.commit()
			print "succesfully added object!"
		except:
			print "IntegrityError"
			session.rollback()
			# session.close()
