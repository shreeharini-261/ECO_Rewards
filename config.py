import os

class Config:
    SECRET_KEY = 'demo-key-123456'  # For demo purposes only
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'ecorewards.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POINT_RULES = {
        'organic': 5,
        'plastic': 10,
        'paper': 7,
        'e-waste': 20,
        'metal': 15
    }