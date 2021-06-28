import os
from server.make_stand_alone import *
import json
import socket
from PrivaChatterDjango.settings import BASE_DIR
from collections import defaultdict
from server.models import *
#from server.tools import *
from _thread import *
from server.criptor import Criptor
import threading

""" 
    Klasa będąca back-end aplikacji po stronie klienta.
:rtype: ClientServer
"""
class ClientServer:
    response = ''
    raw_response = b''


    def __init__(self, login="", password="", new_account=False, auth_now=True, secure_connection=False):
        """
        Creating backend object.

        :param login: login w dowolnej postaci.
        :param password: hasło o długości conajmniej 8 znakow
        :param new_account: Sprecyzuj czy jest to nowe konto czy już obecne
        :param auth_now:
        :param secure_connection:
        """
        CONFIG_FILE = os.path.join(BASE_DIR, 'server', 'socket_settings.json')
        with open(CONFIG_FILE, 'r') as file:
            self.socket_settings = json.load(file)
        self.client_account = None
        self.secure_connection = False
        self.__initialize_keys_dict()

        ##wymiana kluczami z wykorzystaniem algorytmu Diffie–Hellman key exchange
        if secure_connection:
            self.establish_secure_connection(login)
        ##autoryzuj użytkownika
        if auth_now:
            if not new_account:
                self.client_account = self.login(login, password)
            else:
                self.client_account = self.register(login, password)

        self.__initialize_messages_dict()




    def __init_logout(self):
        self.start_time = time.time()
        self.last_action = time.time()
        self.logout_now = False

    def establish_secure_connection(self, login):
        """Create secure connection with server

        :param login: (str)
        :return: result if secured connection is established
        """
        #pobierane są wartości P oraz G ( Diffie–Hellman ) z serwera.
        self.download_public_keys_server(login)
        ## wymiana częściami kluczy oraz generowanie klucza prywatnego
        result = self.exchange_partial_keys_server(login)
        self.secure_connection = result
        return result

    def download_public_keys_server(self, login):
        """Downlod public keys from server

        :param login: (str)
        """
        message = Message(from_=login,
                          to=self.socket_settings["SERVER_EMAIL"],
                          data=None,
                          content_type=None,
                          action_type=ActionType.DOWNLOAD_KEYS)

        self.send_message(message)
        self._create_criptor_object(self.response)

    def _create_criptor_object(self, message):
        """Creating criptor object.

        :param message: (Message) response from method download_public_keys_server
        """
        login = message.get_receiver()
        P, G = message.data[0], message.data[1]
        pair = (login, self.socket_settings["SERVER_EMAIL"])
        self.keys_dict[pair] = Criptor(P, G, self.socket_settings["DEBUG"], 0)


    def exchange_partial_keys_server(self, login):
        """Exchanging partial keys with server. Creating commmon secret key.

        :rtype: (bool): result of creating secret keys for session
        """
        pair = (login, self.socket_settings["SERVER_EMAIL"])
        my_partial_key = self.keys_dict[pair].generate_partial_key()
        message = Message(from_=login,
                          to=self.socket_settings["SERVER_EMAIL"],
                          data=my_partial_key,
                          content_type=ContentType.PARTIAL_KEY,
                          action_type=ActionType.EXCHANGE_KEYS)
        self.send_message(message)
        response = self.response
        if not response.is_error():
            self.keys_dict[login, self.socket_settings["SERVER_EMAIL"]].generate_full_key(response.data)
            return True
        return False

    def __initialize_messages_dict(self):
        """Initialize messages dict
            key = email_from
            values =  set of messages objects"""
        self.received_messages = defaultdict(set)
        self.sent_messages = defaultdict(set)

    def __clear_messages_dict(self):
        """Czyszczenie danych po użytkowniku"""
        if self.received_messages:
            del self.receive_message
        if self.sent_messages:
            del self.sent_messages
        self.__initialize_messages_dict()



    def __initialize_keys_dict(self):
        self.keys_dict = {}

    def register(self, email, password):
        """Register user metgod.

        :param email: (str) email as string
        :param password: (str) password as string
        :return: return account object if register was successful else None
        """
        if not self.secure_connection:
            return None

        message = Message(email, self.socket_settings["SERVER_EMAIL"],
                          ContentType.AUTH_TUPLE,
                          ActionType.REGISTER,
                          'utf-8', 200,
                          (email, password))

        self.send_message(message)
        response = self.get_response()
        self.client_account = response.data
        return response.data

    def send_message(self, message):
        """High level method to sending messages. Encyption takes place here.

        :param message (Message): message object to send
        """
        pair = message.get_sender(), message.get_receiver()
        if self.secure_connection:
            """W przypadku kiedy ruch jest szyfrowany. Szyfrowana jest wiadomość."""
            safe_message = SafeMessage(pair[0], pair[1], message)
            criptor = self.keys_dict[pair]
            safe_message.encrypt_message(criptor)
            raw_message = safe_message.prepare_to_send()
        else:
            raw_message = message.prepare_to_send()

        self.__send_message(raw_message)


    def __send_message(self, data):
        """ low level method to sending messages.

        :param data (bytes): data as bytes to send.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.socket_settings["HOST"], int(self.socket_settings["PORT"])))
            s.sendall(data)
            self.raw_response = self.recive_data(s)

            self.response = self.load_data(self.raw_response)

            s.close()
        except socket.error:
            print('Connection not established.')
            print(sys.exc_info())

    def get_response(self):
        """ get response saved in object

        :return (Message):
        """
        return self.response


    def get_server_email(self):
        return self.socket_settings["SERVER_EMAIL"]


    def logout(self):
        """ Process logout. Remove all stored data.

        :return:
        """
        if not self.client_account:
            return True

        email = self.client_account.email
        message = Message(email, self.socket_settings["SERVER_EMAIL"],
                          ContentType.AUTH_TUPLE,
                          ActionType.LOGOUT,
                          'utf-8', 200,
                          (email, None))

        self.send_message(message)
        response = self.response
        if response.headers['status_code'] == StatusCode.OK:
            return True
        if response.headers['status_code'] == StatusCode.NOTLOGINYET:
            return False
        """Bez względu na wynik usuń wszystkie dane."""
        self.__clear_messages_dict()
        self.client_account = None
        return False

    def login(self, email="", password=""):
        """ Process login.

        :param email: choosen login
        :param password: choosen password
        :return: account object if successful else None
        """
        if not self.secure_connection:
            return None
        """Pozostałości po testowaniu do usunięcia w przyszłośc.
            Usunę to później. W tej chwili może to wykoleić podstawowe testy."""
        email = self.socket_settings["DEFAULT_CLIENT_EMAIL"] if email == "" else email
        password = self.socket_settings["DEFAULT_PASSWORD"] if password == "" else password

        message = Message(email, self.socket_settings["SERVER_EMAIL"],
                          ContentType.AUTH_TUPLE,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          (email, password))

        self.send_message(message)

        response = self.get_response()
        self.client_account = response.data
        return response.data

        pass

    def is_friend_active(self, friend_email):
        """ Get info about user activity.

        :param friend_email: friend email or any login
        :return (bool): is user active or not
        """
        if not self.secure_connection:
            return False

        if not self.client_account:
            return False
        message = Message(self.client_account.email, self.socket_settings["SERVER_EMAIL"],
                          ContentType.CLIENT_OBJECT,
                          ActionType.CHECK_IS_ACTIVE,
                          'utf-8', 200,
                          friend_email)
        self.send_message(message)
        response = self.response
        is_active = True if response.headers['status_code'] == StatusCode.OK else False
        return is_active

    def is_login(self):
        """Check if login was successful

        :return (bool): result of login
        """
        if not self.client_account:
            return False
        try:
            my_email = self.client_account.email
            return self.is_friend_active(my_email)
        except AttributeError as e:
            print(e)
            return False




    def send_message_to_friend(self, friend_email, string_message):
        """ Send text message to friend.

        :param friend_email: login or email of friend
        :param string_message (str): string message.
        :return: result of sending message to server
        """
        message = Message(from_=self.client_account.email,
                          to=self.socket_settings["SERVER_EMAIL"],
                          data=(friend_email, string_message),
                          content_type=ContentType.RECEIVER_MESSAGE_PAIR,
                          action_type=ActionType.SEND_MESSAGE)
        self.send_message(message)
        self.sent_messages[friend_email].add(message)

        response = self.response
        return True if response.headers['status_code'] == StatusCode.OK else False


    def download_message_from_friend(self, friend_email):
        """ Downloading messages send to user by user with login friend_email.
        Messages are saved to received_messages dict.

        :param friend_email (str): string email or login
        :return: result of downloading messages
        """
        server_mail = self.socket_settings["SERVER_EMAIL"]
        message = Message(from_=self.client_account.email,
                          to=server_mail,
                          data=friend_email,
                          content_type=ContentType.EMAIL,
                          action_type=ActionType.DOWNLOAD_MESSAGES)
        self.send_message(message)
        response = self.response
        self.add_messages_to_dict(response.data)

        return True if response.headers['status_code'] == StatusCode.OK else False


    def add_messages_to_dict(self, messages):
        """Adding messages to received messages container

        :param messages:
        """
        if messages is None:
            return
        if isinstance(messages, list):
            for message in messages:
                self.received_messages[message.get_sender()].add(message)


    def get_messages(self, friend_email):
        """get messages as list"""
        if self.received_messages:
            return self.received_messages[friend_email]
        else:
            return None

    def recive_data(self, client):
        """Receive data from connection

        :param client (socket): client as socket object
        :return (bytes): received bytes
        """
        data = b''
        CRCN_b = b'\r\n\r\n'
        while CRCN_b not in data:
            buffor = client.recv(512)
            data += buffor
            if not buffor:
                break
        return data

    def load_data(self, data):
        """Bytes to object.

        :param data(bytes):
        :return (Message): Message object
        """
        if b'\r\n\r\n' in data:
            return pickle.loads(data[:-4])
        else:
            return pickle.loads(data)

    def prepare_conversation_with(self, friend):
        """Preparing conversation as string to show on screen.

        :param friend: friend email
        :return:
        """
        self.download_message_from_friend(friend)
        my_sent_messages = self.sent_messages[friend]
        from_friend = self.get_messages(friend)

        if from_friend:
            messages = list(my_sent_messages) + list(from_friend)
        else:
            messages = list(my_sent_messages)

        messages.sort(key=lambda x: x.creation_time)
        text = ""
        for message in messages:
            tmp = f"{message.get_sender()}: {message.data[1]}\n"
            text += tmp

        return text