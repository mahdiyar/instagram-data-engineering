from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	user_id = Column(String(80), nullable=False, unique=True)
	username = Column(String(80), nullable=False, unique=True)
	bio = Column(Text)
	num_followers = Column(Integer)
	num_following = Column(Integer)
	num_posts = Column(Integer)
	latitude = Column(String(80))
	longitude = Column(String(80))

	## Relationships
	user = relationship('User')

class Media(Base):
	__tablename__ = 'media'

	id = Column(Integer, primary_key=True)
	user_id = Column(String(80), ForeignKey('user.user_id'), nullable=False, unique=True)
	media_id = Column(String(280), nullable = False, unique=True)
	num_likes = Column(Integer)
	num_comments = Column(Integer)
	latitude = Column(String(80))
	longitude = Column(String(80))
	caption = Column(Text, default='')

	## Relationships
	instagram_user = relationship('User')

class Follower(Base):
	__tablename__ = 'follower'

	id = Column(Integer, primary_key=True)
	user_id = Column(String(80), ForeignKey('user.user_id'), nullable=False)
	follower_id = Column(String(80), ForeignKey('user.user_id'), nullable=False)

	__table_args__ = (UniqueConstraint('user_id', 'follower_id', 
						name='_following_uc'),)

	## Relationships
	instagram_user = relationship('User')


engine = create_engine('sqlite:///instagram.sqlite')
Base.metadata.create_all(engine)