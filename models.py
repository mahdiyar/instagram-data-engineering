import cnfg
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists
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

################################################################
#################      Helper functions        #################
################################################################

def get_user_id(username):
	""" Given a instagram username, return the instagram_id."""

	user_search = api.user_search(q=username)
	user_ids = {user.__dict__['username']:user.id for user in user_search}
	return str(user_ids[username])

def rate_limit_check():
	""" Ping the instagram api and return the rate limit."""

	user_search = api.user_search(q='instagram')
	remaining_calls = int(api.x_ratelimit_remaining)
	return remaining_calls

def commit_to_db(new_object):
	""" Commit new object to the database."""

	try:
		session.add(new_object)
		session.commit()
		print "Succesfully added object!"
	except IntegrityError:
		print "IntegrityError"
		session.rollback()
		# session.close()

def user_exists(instagram_id):
	""" This function checks to see if a user exists in the instagram user
		table. If they do, it returns their user object. Otherwise it returns
		None. """

	# Query database to see if instagram_id exists in instagram_user table.
	user_exists = session.query(exists()\
					 .where(InstagramUser.instagram_id==instagram_id))\
					 .scalar()
	if user_exists:
		user = session.query(InstagramUser)\
				   .filter_by(instagram_id=instagram_id)\
				   .one()
		return user
	else:
		return None

################################################################
########## Classes to pull and store Instagram data ############
################################################################

class AddUserProfile():
	'''This class takes a instagram_id and grabs a user's profile information
	   stores it in the database.'''

	def __init__(self,instagram_id,user_order):
		self._instagram_id = instagram_id
		self._user_order = user_order
		# Grab and store a user's basic profile data.

		if user_exists(self._instagram_id):
			print 'User data: user profile already in database.'
			pass
		else:
			try:
				print 'User data: storing user profile and media in database.'
				basics, _ = self._get_user_profile()
				media, rate = self._get_user_media()
				print rate
				self._store_user(basics)
				self._store_media(media)
			except InstagramAPIError:
				print 'Private: this user is private.'

	def _get_user_profile(self):
		''' Returns a tuple including a dictionary with instagram user data
			stored for a given user_id and the remaining amount of calls
			available to make on the api. If the user's account
			is private this will return (None, None).'''

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

	def _get_user_media(self):
		''' Given an instagram user id, this return a tuple including a list 
			of dictionaries containing data on the user's recent media and 
			the amount of remaining calls available to make on the api. If 
			the user's account is private this will return (None, None).
		'''

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

		user = user_exists(self._instagram_id)
		if user:
			if not self._follower_count_within_range(.1):
				# Grab and store a user's list of followers.
				followers, remaining_calls = self._get_user_followers()
				print remaining_calls
				self._store_followers(followers)
			else:
				print 'Followers: Count of followers is within bound.'
				pass
		else: 
			print 'not stroring followers: user not in db'

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

	def _follower_count_within_range(self,prec_range):
		""" This function checks the database to see if the number of followers
			in the Follower table is within a range of the current number in 
			the user's profile."""

		followers = session.query(Follower)\
						   .filter_by(instagram_id=self._instagram_id)
		db_count = followers.count()
		user = session.query(InstagramUser)\
					  .filter_by(instagram_id=self._instagram_id)\
					  .one()
		prof_count = user.num_followers
		bound = prof_count*prec_range

		return prof_count-bound <= db_count <= prof_count+bound

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

		# Check if there are already enough of the users following
		# in the database.
		user = user_exists(self._instagram_id)
		if user:
			if not self._follows_count_within_range(.1):
				# Grab and store the list of user follows.
				follows, remaining_calls = self._get_user_follows()
				print remaining_calls
				self._store_follows(follows)
			else:
				print 'Follows: Count of following is within bound.'
				pass
		else:
			print 'not stroring follows: user not in db'

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

	def _follows_count_within_range(self,prec_range):
		""" This function checks the database to see if the number of follows
			in the Follower table is within a range of the current number in 
			the user's profile."""

		follows = session.query(Follower)\
						   .filter_by(follower_id=self._instagram_id)
		db_count = follows.count()
		user = session.query(InstagramUser)\
					  .filter_by(instagram_id=self._instagram_id)\
					  .one()
		prof_count = user.num_following
		bound = prof_count*prec_range

		return prof_count-bound <= db_count <= prof_count+bound


################################################################
########## Classes that pull various orders of data  ###########
################################################################

class CandidateDataPull():
	""" This is a class that pulls the data necessary to analyze the canddates
		(these are the users that followers follow). This is a third order
		data pull. Pass in a instagram id and it will pull and store the
		user's profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=3):
		self._instagram_id = instagram_id
		self._user_order = user_order

		AddUserProfile(self._instagram_id,self._user_order)


class TargetDataPull():
	""" This is a class that pulls the all of the data necessary to
		analyze the target customer. This is the second order data pull.
		Pass in a instagram id and it will pull and store the user's
		profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=2):
		self._instagram_id = instagram_id
		self._user_order = user_order

		# Checking whether the user already exists in the database.
		user = user_exists(self._instagram_id)
		if user:
			if user.user_order <= 2:
				print 'order 1 or 2 user already exists'
				pass
			else:
				print 'in order 3 full pull'
				self._partial_3_2_pull()
				self._update_order_to_2()
		else:
			print 'new user-- full 2 pull'
			self._full_2_pull()

	def _full_2_pull(self):
		AddUserProfile(self._instagram_id,self._user_order)
		AddUserFollows(self._instagram_id)

		follows = self._get_list_follows()
		for follow_id in follows:
			CandidateDataPull(follow_id)
	
	def _partial_3_2_pull(self):
		AddUserFollows(self._instagram_id)

		follows = self._get_list_follows()
		for follow_id in follows:
			CandidateDataPull(follow_id)

	def _get_list_follows(self):
		q = session.query(Follower).filter_by(follower_id=self._instagram_id)
		follows = [relationship.instagram_id for relationship in q]
		return follows

	def _update_order_to_2(self):
		instagram_user = session.query(InstagramUser)\
							    .filter_by(instagram_id=self._instagram_id)\
							    .one()
		instagram_user.user_order = 2
		commit_to_db(instagram_user)

class InfluencerDataPull():
	""" This is a class that pulls the all of the data necessary to
		analyze the influencer. This is the first order data pull.
		Pass in a instagram id and it will pull and store the user's
		profile, recent media, and what accounts they follow."""

	def __init__(self,instagram_id,user_order=1):
		self._instagram_id = instagram_id
		self._user_order = user_order

		# Checking whether the user already exists in the database.
		user = user_exists(self._instagram_id)

		if user:
			if user.user_order == 2:
				print 'in order 2 partial pull'
				self._partial_2_1_pull()
				self._update_order_to_1()
			elif user.user_order == 3:
				print 'in order 3 full pull'
				self._partial_3_1_pull()
				self._update_order_to_1()
			else:
				assert user.user_order == 1
				if not user.pull_completion:
					self._full_1_pull()
				else:
					print 'already have user at order 1, no pull'
					pass
		else:
			print 'in new user-- full pull'
			self._full_1_pull()
			

	def _full_1_pull(self):
		## full pul of all the data
		AddUserProfile(self._instagram_id,self._user_order)
		AddUserFollowers(self._instagram_id)
		AddUserFollows(self._instagram_id)

		followers = self._get_list_followers()
		for follower_id in followers:
			TargetDataPull(follower_id)

		follows = self._get_list_follows()
		for follow_id in follows:
			CandidateDataPull(follow_id)

	def _partial_3_1_pull(self):
		AddUserFollowers(self._instagram_id)
		AddUserFollows(self._instagram_id)

		followers = self._get_list_followers()
		for follower_id in followers:
			TargetDataPull(follower_id)

		follows = self._get_list_follows()
		for follow_id in follows:
			CandidateDataPull(follow_id)

	def _partial_2_1_pull(self):
		## partial pull because already have follows
		AddUserFollowers(self._instagram_id)

		followers = self._get_list_followers()
		for follower_id in followers:
			TargetDataPull(follower_id)

	def _get_list_followers(self):
		q = session.query(Follower).filter_by(instagram_id=self._instagram_id)
		followers = [relationship.follower_id for relationship in q]
		return followers

	def _get_list_follows(self):
		q = session.query(Follower).filter_by(follower_id=self._instagram_id)
		follows = [relationship.instagram_id for relationship in q]
		return follows

	def _update_order_to_1(self):
		## updates the user order
		instagram_user = session.query(InstagramUser)\
							    .filter_by(instagram_id=self._instagram_id)\
							    .one()
		instagram_user.user_order = 1
		commit_to_db(instagram_user)


