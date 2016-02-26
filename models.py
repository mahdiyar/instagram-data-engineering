import cnfg
from instagram.client import InstagramAPI

config = cnfg.load(".instagram_config")
api = InstagramAPI(client_id=config['CLIENT_ID'], client_secret=config['CLIENT_SECRET'])

key_username = 'knowlita'

def get_user_id(username):
	''' Given a username, return the instagram user_id.
		Only returns exact match. '''

	user_search = api.user_search(q=username)
	return user_search[0].id

def get_user_basics(user_id):
	''' Returns the instagram user object for a user_id'''

	basics = {'user_id' : user_id}
	user = api.user(user_id = user_id)

	# Extract data and store in dict
	basics['username'] = user.username
	basics['bio'] = user.bio
	basics['followers_count']= user.counts['followed_by']
	basics['follows_count'] = user.counts['follows']
	basics['media_count'] = user.counts['media']

	return basics


print get_user_basics(get_user_id(key_username))