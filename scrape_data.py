import cnfg
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from instagram.client import InstagramAPI

from db_setup import User, Media, Follower

# Setting the database connection.
engine = create_engine('sqlite:///instagram.sqlite')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()

# Configuring the instagram client
config = cnfg.load(".instagram_config")
api = InstagramAPI(client_id=config['CLIENT_ID'], 
				   client_secret=config['CLIENT_SECRET'])

