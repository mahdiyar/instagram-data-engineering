import cnfg
from instagram.client import InstagramAPI
from pprint import pprint 

config = cnfg.load(".instagram_config")
api = InstagramAPI(client_id=config['CLIENT_ID'], client_secret=config['CLIENT_SECRET'])

basics = api.user('332324252')
pprint(basics.bio)