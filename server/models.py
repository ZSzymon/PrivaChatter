import sys
from enum import Enum
from datetime import datetime
import json
import pickle
import time
import copy
import hashlib
import warnings
import functools
try:
    from django.db import models
    from django.conf import settings
except Exception:
    print('Exception: Django Not Found, please install it with "pip install django".')
    sys.exit()



class Account(models.Model):
    """Account model.

    :arg email:       email is most important.
    :arg username:    not important. Type anything
    :arg password:    password as hash.
    :arg is_active:   is account currently active
    :arg is_authenticated: is account authenticated
    """
    email = models.EmailField(unique=True, primary_key=True, default='')
    username = models.CharField(max_length=50, default="")
    password = models.CharField(max_length=50, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    is_authenticated = models.BooleanField(default=False)
    friendsJsonString = models.TextField(null=True, blank=True, default="")
    friends = list()

    @staticmethod
    def create_from_dict(serialized_dict):
        """Create dict Account object from serialized dict.

        :param serialized_dict: output for to_dict method
        """
        account_dict = serialized_dict
        account = Account(email='')
        for key, val in account_dict.items():
            if key != '_state':
                setattr(account, key, val)

    @staticmethod
    def to_dict(obj):
        """
        :param obj: create dict from obj
        :return:
        """
        return vars(obj)

    class Meta:
        db_table = "account"


    def __validate_password(self, password1, password2):
        """Password validations.

        :param password1: first password
        :param password2: second password
        :return:
        """
        conditions_results = []
        conditions_results.append(password1 == password2)
        # conditions_results.append(password1[0].isupper())
        # reszta warunków.

        return all(condition for condition in conditions_results)


    def __str__(self):
        return self.email


    def set_friends_list(self, friends: list):
        """Setting friends list on order to store in database

        :param friends: list of friends
        """
        self.friendsJsonString = json.dumps(friends)
        self.save()


    def get_friends_list(self):
        """Getting list of friends.

        :return:
        """
        return json.loads(self.friendsJsonString)


class ActionType(Enum):
    """Actions type enum.
    Example message.set_action_type(ActionType.NONE)

    """
    REGISTER = 1,
    LOGIN = 2,
    SEND_AUTHORIZE_CODE = 3,
    AUTH_USER = 4,
    NONE = 5,
    TEST = 6,
    CHECK_IS_ACTIVE = 7,
    RESPONSE = 8,
    LOGOUT = 9,
    SEND_MESSAGE = 10,
    DOWNLOAD_MESSAGES = 11
    EXCHANGE_KEYS = 12,
    DOWNLOAD_KEYS = 13



class ContentType(Enum):
    """Content type enumaration for messages.

    """
    TEXT_ENCODED = 1,
    CLIENT_OBJECT_AS_DICT = 2,
    CLIENT_OBJECT = 3,
    EMAIL = 4,
    AUTH_TUPLE = 5,
    EMPTY = 6,
    SECURE_MESSAGES = 7,
    PLAIN_MESSAGES = 8,
    NONE = 9,
    PUBLIC_KEY = 10,
    ERROR_MESSAGE = 11,
    PARTIAL_KEY = 12,
    RECEIVER_MESSAGE_PAIR = 13


class StatusCode(Enum):
    """Status code enumeration. Used in messages.

    """
    OK = 200,
    CREATED = 201,
    UNAUTHORIZED = 401,
    FORBIDDEN = 403,
    NOTFOUND = 404,
    ERROR = 405
    USER_EXIST = 501,
    NOTLOGINYET = 502,
    UNSUPPORTEDMEDIATYPE = 415



class SecureLevel(Enum):
    """
    Not used.
    """
    UNENCRYPTED = 1,
    ENCRYPTED = 2,



class SafeMessage():
    """Encrypted message class
      From intercepted message is possible to get email sender and receiver.

    """
    def __init__(self, _from, _to, message=None):
        """

        :param _from (str): sender email
        :param _to (str): receiver email
        :param message (Message): message object.
        """
        ##do not add double crlf at end of pickled message.
        self.message = message.prepare_to_send(True)
        self._from = _from
        self._to = _to

    def prepare_to_send(self):
        """ Preparing message to send over network.

        :return (bytes): Encrypted message.
        """
        CRLF= '\r\n'
        raw_message = pickle.dumps(self)
        raw_message += f'{CRLF}{CRLF}'.encode('utf-8')
        return raw_message

    def get_pair(self):
        return self._to, self._from


    def encrypt_message(self, criptor):
        """Function to encrypt message

        :param criptor: criptor object used for encryption
        """
        self.message = criptor.encrypt_message(self.message)

    def decrypt_message(self, criptor):
        """Decrptiong message function

        :param criptor: criptor object used for decryption
        """
        self.message = criptor.decrypt_message(self.message)



class Message:
    """Not encrypted message class

    """
    CRLF = '\r\n'

    def __init__(self, from_='', to='',
                 content_type='',
                 action_type=ActionType.NONE,
                 encoding='utf-8',
                 status_code=200,
                 data=''
                 ):
        """Initialize message object

        :param from_: sender mail
        :param to: receiver mail
        :param content_type: specify content type
        :param action_type: specify what server does with message
        :param encoding: Support only utf-8
        :param status_code: Server response result.
        :param data: data to send.
        """
        self.headers = dict()
        self.headers['to'] = to
        self.headers['from_'] = from_
        self.headers['content_type'] = content_type
        self.headers['action_type'] = action_type
        self.headers['encoding'] = encoding
        self.headers['status_code'] = status_code
        self.headers['secure_level'] = SecureLevel.UNENCRYPTED
        self.data = data
        self.creation_time = time.time()
        self.creation_date = datetime.fromtimestamp(self.creation_time).strftime("%Y %I:%M:%S")

        pass

    def deepcopy(self):
        object_copy = copy.deepcopy(self)
        object_copy.creation_time = time.time()
        return object_copy

    def set_secure_level(self, secure_level: SecureLevel):
        """Not used

        :param secure_level (SecureLevel): enum
        """
        self.headers['secure_level'] = secure_level

    def get_secure_level(self):
        return self.headers['secure_level']

    def set_action_type(self, action_type: ActionType):
        """Easy setting action type.

        :param action_type (ActionType): action type value.
        """
        self.headers['action_type'] = action_type


    def get_action_type(self):
        return self.headers['action_type']

    def set_content_type(self, content_type: ContentType):
        self.headers['content_type'] = content_type

    def get_content_type(self):
        return self.headers['content_type']

    def get_data(self):
        return self.data

    def get_receiver(self):
        return self.headers['to']

    def get_sender(self):
        return self.headers['from_']

    def prepare_to_send(self, use_as_safe= False):
        """ Dumps message to bytes.

        :param use_as_safe (bool): specify is this message used in encrypted traffic. (Use only if this message is part of Safe Message)
        :return (bytes): message as pickled bytes.
        """
        raw_message = pickle.dumps(self)
        if not use_as_safe:
            raw_message += f'{self.CRLF}{self.CRLF}'.encode('utf-8')
        return raw_message

    def is_error(self):
        return self.headers['status_code'] == StatusCode.ERROR



    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Message):
            return self.creation_time == other.creation_time
        return False

    def __hash__(self):
        '''Wiem że to łamanie wszystki zasad.
        Zastsowałem to aby nie duplikowały się wiadomości w setach.'''
        return int(self.creation_time)


    def swap_sender_receiver(self):
        old_receiver = self.get_receiver()
        self.headers['to'] = self.headers['from_']
        self.headers['from_'] = old_receiver
