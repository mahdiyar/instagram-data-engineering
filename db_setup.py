from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class InstagramUser(Base):
	__tablename__ = 'instagram_user'

	id = Column(Integer,primary_key=True)
	instagram_id = Column(String(80),nullable=False,unique=True)
	instagram_username = Column(String(80),nullable=False,unique=True)
	bio = Column(Text)
	num_followers = Column(Integer)
	num_following = Column(Integer)
	num_posts = Column(Integer)
	latitude = Column(String(80))
	longitude = Column(String(80))

	## Relationships
	follower = relationship('Follower', backref="instagram_user")
	media = relationship('Media', backref="instagram_user")
	influencer = relationship('Influencer', backref="instagram_user")
	client = relationship('Client', backref="instagram_user")
	target_audience = relationship('TargetCustomer', backref="instagram_user")

class Media(Base):
	__tablename__ = 'media'

	id = Column(Integer, primary_key=True)
	instagram_id = Column(String(80), ForeignKey('instagram_user.instagram_id'), nullable=False)
	media_id = Column(String(280), nullable = False, unique=True)
	num_likes = Column(Integer)
	num_comments = Column(Integer)
	latitude = Column(String(80))
	longitude = Column(String(80))
	caption = Column(Text, default='')

class Follower(Base):
	__tablename__ = 'follower'

	id = Column(Integer, primary_key=True)
	instagram_id = Column(String(80),ForeignKey('instagram_user.instagram_id'),nullable=False)
	follower_id = Column(String(80),nullable=False)

	__table_args__ = (UniqueConstraint('instagram_id', 'follower_id', 
						name='_following_uc'),)

class Influencer(Base):
	__tablename__='influencer'

	id = Column(Integer,primary_key=True)
	instagram_id = Column(String(80),ForeignKey('instagram_user.instagram_id'),nullable=False)


class Client(Base):
	__tablename__='client'

	id = Column(Integer,primary_key=True)
	instagram_id = Column(String(80),ForeignKey('instagram_user.instagram_id'),nullable=True)

	campaign = relationship('Campaign', backref="client")


class Campaign(Base):
	__tablename__='campaign'

	id = Column(Integer, primary_key=True)
	client_id = Column(Integer,ForeignKey('client.id'),nullable=False)
	title = Column(String(200),nullable=False)
	description = Column(Text,nullable=False)
	compensation = Column(Text,nullable=False)
	target_customer_id = Column(Integer,ForeignKey('target_customer.id'),nullable=False)


class TargetCustomer(Base):
	__tablename__='target_customer'

	id = Column(Integer,primary_key=True)
	instagram_id = Column(String(80),ForeignKey('instagram_user.instagram_id'),nullable=False)

	campaign = relationship('Campaign', backref="target_customer")




engine = create_engine('postgresql://localhost/metis_adsthetic')
Base.metadata.create_all(engine)