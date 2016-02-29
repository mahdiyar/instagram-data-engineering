import cnfg
from instagram.client import InstagramAPI
from instagram.bind import InstagramAPIError

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
		stored for a given user_id'''

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



##### Get an instagram user's list of follwers



key_username = 'eglum'
key_id = get_user_id(key_username)

test_followers = get_user_followers(key_id)
