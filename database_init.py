from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from database_setup import *

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Delete Categories if exisitng.
session.query(Category).delete()
# Delete Items if exisitng.
session.query(Items).delete()
# Delete Users if exisitng.
session.query(User).delete()

# Create sample users
User1 = User(name="Tilak Babu",
             email="babutilak234@gmail.com",
             picture='https://lh4.googleusercontent.com'
             '/-Rq6f1CG7vls/AAAAAAAAAAI/AAAAAAABGBQ/voOw-3oZvhQ/photo.jpg')
session.add(User1)
session.commit()


# Create sample categories
Category1 = Category(name="Car & Motor Bikes",
                     user_id=1)
session.add(Category1)
session.commit()

Category2 = Category(name="Gadgets",
                     user_id=1)
session.add(Category2)
session.commit

Category3 = Category(name="Clothing",
                     user_id=1)
session.add(Category3)
session.commit()

Category4 = Category(name="Apps & Games",
                     user_id=1)
session.add(Category4)
session.commit()

Category5 = Category(name="Music",
                     user_id=1)
session.add(Category5)
session.commit()


# Populate a category with items for testing
# Using different users for items also
Item1 = Items(name="Mobile",
              date=datetime.datetime.now(),
              description="4 GB RAM | 64 GB ROM | Expandable Upto"
              " 128 GB 5.99 inch Full HD+ Display 12MP Rear Camera"
              " | 5MP Front Camera 4000 mAh Li Polymer Battery"
              " Qualcomm Snapdragon 625 Processor",
              picture="https://rukminim1.flixcart.com/image"
              "/832/832/jdkjzww0/mobile/u/y/j/redmi-note-5-"
              "mzb5916in-original-imaf2gabuvmuhvrz.jpeg?q=70",
              category_id=2,
              user_id=1)
session.add(Item1)
session.commit()

Item2 = Items(name="Jai Textiles Men's Solid Casual Spread Shirt",
              date=datetime.datetime.now(),
              description="Premium cuts, forms and colors combined "
              "with exquisite fabrics in finest workmanship emblematic "
              "the highest standards regarding quality and style of the "
              "collection bearing the brand of Jai Textiles. The high "
              "quality and soft easy-iron fabric is brea",
              picture="https://ae01.alicdn.com/kf/"
              "HTB1QoQ0QFXXXXXYapXXq6xXFXXX3/Men-s-Shirts-Cotton-"
              "Red-Shirt-Men-Casual-Camisas-Hombre-Clothing-2018-"
              "Fashion-Red-Dress-Shirt.jpg_640x640.jpg",
              category_id=3,
              user_id=1)
session.add(Item2)
session.commit()

Item3 = Items(name="CENTY Hindustan Ambassador Car  (Multicolour)",
              date=datetime.datetime.now(),
              description="Designed in the style of age old car, "
              "Ambassador car by Hindustan Motors, this toy car by"
              " Centy Toy will assure you a smooth play. Black and "
              "yellow, just authentic as the real one, the mini toy"
              "features intricate detailing. You cannot resist gifting",
              picture="https://rukminim1.flixcart.com/image/832/832/"
              "jd94h3k0/vehicle-pull-along/q/v/b/"
              "hindustan-ambassador-car-centy-"
              "original-imaf22pgph4tkkx9.jpeg?q=70",
              category_id=1,
              user_id=1)
session.add(Item3)
session.commit()

print("Your database has been populated with sample data!")
