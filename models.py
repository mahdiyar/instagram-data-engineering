import math
import cnfg

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists
from sqlalchemy.exc import IntegrityError
from instagram.client import InstagramAPI
from instagram.bind import InstagramAPIError

from datetime import datetime

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
	user_ids = {user.__dict__['username']:user.id for user in user_search}
	return str(user_ids[username])

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

	def __init__(self,instagram_id,user_order):
		self._instagram_id = instagram_id
		self._user_order = user_order
		# Check to see if user is in already in database. 
		ret = session.query(exists()\
					 .where(InstagramUser.instagram_id==self._instagram_id))\
					 .scalar()
		if not ret:
			print 'Storing new user'
			# Grab and store a user's basic profile data.
			basics, rate = self._get_user_profile()
			print rate
			self._store_user(basics)
		else:
			print 'User aleady in DB'

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
			instagram_user_profile['instagram_username'] = instagram_user.username
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
			new_user = InstagramUser(instagram_id=self._instagram_id,
							instagram_username=instagram_user_profile['instagram_username'],
							bio=instagram_user_profile['bio'],
							num_followers=instagram_user_profile['num_followers'],
							num_following=instagram_user_profile['num_following'],
							num_posts=instagram_user_profile['num_posts'],
							user_order=self._user_order,
							stored_at=datetime.now())
			commit_to_db(new_user)


class AddUserMedia():
	''' This class takes an instagram_id and grabs the user's recent media
		and stores all of this information in the database.'''

	def __init__(self,instagram_id):
		self._instagram_id = instagram_id
		# Check to see if media exists in Database. Can be made smarter to 
		# make sure a certain amount exists. 

		ret = session.query(exists()\
					 .where(Media.instagram_id==self._instagram_id))\
					 .scalar()
		if not ret:
			# Grab and store a user's recent media data.
			print 'Storing user media'
			media, _ = self._get_user_media()
			self._store_media(media)
		else:
			print 'Media for this user already exists.'


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
				new_follower = Follower(instagram_id=self._instagram_id,
										follower_id=follower_id)
				commit_to_db(new_follower)

class AddUserFollows():
	""" This class defines the methods to pull the list of users that a given
		instagram user follows. So input is a instagram_id and stores the
		relationships in the Follwer table."""

	def __init__(self,instagram_id):
		self._instagram_id = instagram_id

		# Grab and store the list of user follows.
		follows, remaining_calls = self._get_user_follows()
		print remaining_calls
		self._store_follows(follows)

	def _get_user_follows(self):
		""" Given an instagram_id, this will return a tuple containing 
			the list of users that the given account follows, and the 
			count of remaining_calls available to make on the api."""

		try:
			user_follows_list = []
			follows, next = api.user_follows(user_id=self._instagram_id)
			remaining_calls = int(api.x_ratelimit_remaining)
			print remaining_calls
			for user in follows:
				user_follows_list.append(user.id)
			while next:
				follows, next = api.user_follows(with_next_url=next)
				remaining_calls = int(api.x_ratelimit_remaining)
				print remaining_calls	
				for user in follows:
					user_follows_list.append(user.id)
			return user_follows_list, remaining_calls
		
		except InstagramAPIError:
			print 'This user is private'
			return None, None		


	def _store_follows(self,user_follows_list):
		""" A method that stores the follow relationship as a directed 
			pair in the database."""

		if user_follows_list:
			for instagram_id in user_follows_list:
				new_relationship = Follower(instagram_id=instagram_id,
											follower_id=self._instagram_id)
				commit_to_db(new_relationship)


class CandidateDataPull():
	""" This is a class that pulls the data necessary to analyze the canddates
		(these are the users that followers follow). This is a third order
		data pull. Pass in a instagram id and it will pull and store the
		user's profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=3):
		self._instagram_id = instagram_id
		self._user_order = user_order

		AddUserProfile(self._instagram_id,self._user_order)
		AddUserMedia(self._instagram_id)

class TargetDataPull():
	""" This is a class that pulls the all of the data necessary to
		analyze the target customer. This is the second order data pull.
		Pass in a instagram id and it will pull and store the user's
		profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=2):
		self._instagram_id = instagram_id
		self._user_order = user_order

		AddUserProfile(self._instagram_id,self._user_order)
		AddUserMedia(self._instagram_id)
		AddUserFollows(self._instagram_id)

		follows = self._get_list_follows()
		for follow_id in follows:
			CandidateDataPull(follow_id)

	def _get_list_follows(self):
		q = session.query(Follower).filter_by(follower_id=self._instagram_id)
		follows = [relationship.instagram_id for relationship in q]
		return follows

class InfluencerDataPull():
	""" This is a class that pulls the all of the data necessary to
		analyze the influencer. This is the first order data pull.
		Pass in a instagram id and it will pull and store the user's
		profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=1):
		self._instagram_id = instagram_id
		self._user_order = user_order

		AddUserProfile(self._instagram_id,self._user_order)
		AddUserMedia(self._instagram_id)
		AddUserFollowers(self._instagram_id)

		followers = self._get_list_followers()
		for follower_id in followers:
			TargetDataPull(follower_id)


	def _get_list_followers(self):
		q = session.query(Follower).filter_by(instagram_id=self._instagram_id)
		followers = [relationship.follower_id for relationship in q]
		return followers








