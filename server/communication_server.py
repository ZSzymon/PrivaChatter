import os
import json
import socket
import copy
from server.make_stand_alone import *
from PrivaChatterDjango.settings import BASE_DIR
from collections import defaultdict
from server.models import *
from server.criptor import Criptor
from _thread import *
import threading


class CommunicationServer:
    """Server backends.

    """

    def __init__(self):
        CONFIG_FILE = os.path.join(BASE_DIR, 'server', 'socket_settings.json')
        with open(CONFIG_FILE, 'r') as file:
            socket_settings = json.load(file)
        self.HOST = socket_settings['HOST']
        self.PORT = int(socket_settings['PORT'])
        self.server_account = Account.objects.filter(email=socket_settings['SERVER_EMAIL']).first()
        ## in future can swap to store hash instead of plain email.
        self.active_users = set()  # store emails of active users.
        self.DEBUG = socket_settings['DEBUG']
        self.__init_messages_dict()
        self.__initialize_keys_dict()
        self.socket_settings = socket_settings
        self.handler_lock = allocate_lock()
        self.pickle_lock = allocate_lock()

    def __init_messages_dict(self):
        """Initialize dict and locks for messages.

        """
        self.messages_lock = allocate_lock()
        'key = (from -> to)'
        self.messages_dict = defaultdict(list)
        self.conversation_pairs_lock = allocate_lock()
        self.conversation_pairs = defaultdict(set)

    def __initialize_keys_dict(self):
        """Initilize keys dict and lock.
           Keys: my_mail, receiver_emial
           val: criptor object
        """

        self.keys_lock = allocate_lock()
        self.keys_dict = {}

    def get_messages(self, receiver_email, sender_email):
        """Get messages from friend to receiver. Thread safe.

        :param receiver_email (str): receiver mail
        :param friend_email (str): sender mail
        :return List<Message>: list of messages send from sender to receiver
        """
        with self.messages_lock:
            messages = self.messages_dict[(sender_email, receiver_email)]
        return messages
        pass

    def append_messages(self, message):
        """Append messages to dictionary. Thread safe.

        :param message:
        """
        receiver = message.data[0]
        sender = message.get_sender()
        with self.messages_lock:
            self.messages_dict[(sender, receiver)].append(message)
        with self.conversation_pairs_lock:
            self.conversation_pairs[sender].add(receiver)

    def remove_messages(self, email):
        """Remove messages send by user with email. Thread Safe

        :param email: whom mail are going to be removed
        """
        with self.conversation_pairs_lock:
            receivers = self.conversation_pairs[email]
        with self.messages_lock:
            for receiver in receivers:
                self.messages_dict[(email, receiver)].clear()

    def remove_keys_dict_pair(self, pair):
        with self.keys_lock:
            self.keys_dict.pop(pair)

    def get_server_account(self):
        return self.server_account

    def get_response(self):
        return self.response

    def recive_data(self, client):
        """Receive data from client socket.

        :param client: client socket
        :return:
        """
        data = b''
        CRCN_b = b'\r\n\r\n'
        while CRCN_b not in data:
            buffor = client.recv(512)
            data += buffor
            if not buffor:
                break
        return data

    def handle_connection(self, client):
        """Handle connection.

        :param client: client socket
        """
        try:
            while True:
                raw_message = self.recive_data(client)
                response = self.handle_message(raw_message)
                client.sendall(response)
                client.close()
                break

        except KeyboardInterrupt:
            s.close()

    def main_loop(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind((self.HOST, int(self.PORT)))
        except socket.error as e:
            print(str(e))
        server_socket.listen(5)
        while True:
            try:
                client, addr = server_socket.accept()
                print("Connected: " + addr[0])
                start_new_thread(self.handle_connection, (client,))
            except Exception as e:
                print('Exit from loop')
                # break
                print(e)
                pass

    def handle_message(self, raw_message):
        """Handle message. Process message and return response.

        :param raw_message (bytes): message/safe message object as bytes
        :return: response
        """
        if type(raw_message) == Message:
            unpacked_message = raw_message
        else:
            unpacked_message = self.load_data(raw_message)

        if type(unpacked_message) == Message:
            message = unpacked_message
        else:
            message = unpacked_message.message
            pair = unpacked_message.get_pair()

            with self.keys_lock:
                criptor = self.keys_dict[pair]
            message = criptor.decrypt_message(message)
            message = self.load_data(message)

        with self.handler_lock:
            if message.headers['action_type'] == ActionType.LOGIN:
                response = self.handle_login(message)
            elif message.headers['action_type'] == ActionType.CHECK_IS_ACTIVE:
                response = self.handle_check_is_active(message)
            elif message.headers['action_type'] == ActionType.REGISTER:
                response = self.handle_register(message)
            elif message.headers['action_type'] == ActionType.LOGOUT:
                response = self.handle_logout(message)
            elif message.headers['action_type'] == ActionType.SEND_MESSAGE:
                response = self.handle_send_message(message)
            elif message.headers['action_type'] == ActionType.DOWNLOAD_MESSAGES:
                response = self.handle_download_messages(message)
            elif message.headers['action_type'] == ActionType.DOWNLOAD_KEYS:
                response = self.handle_download_keys(message)
            elif message.headers['action_type'] == ActionType.EXCHANGE_KEYS:
                response = self.handle_keys_exchange(message)
            else:
                response = Message(self.server_account.email, message.get_sender(),
                                   ContentType.CLIENT_OBJECT,
                                   ActionType.RESPONSE, 'pickle',
                                   400, client_account)
        response = response.prepare_to_send()

        return response

    def handle_download_keys(self, message):
        """downloading keys handler

        :param message: Message object
        :return:
        """

        ## tworzenie odpowiedzi. Nie związane z samym algorytmem
        response = message.deepcopy()
        response.swap_sender_receiver()
        response.set_action_type(ActionType.RESPONSE)

        #Jako data podanie kluczy publicznych.
        if message.get_action_type() == ActionType.DOWNLOAD_KEYS:
            data = (self.socket_settings["P"], self.socket_settings["G"])
            response.data = data
            response.set_content_type(ContentType.PUBLIC_KEY)
        return response

    def handle_keys_exchange(self, message):
        """ Exchenge keys with user. If login return error response

        :param message:
        :return: response
        """
        ## tworzenie odpowiedzi. Nie związane z samym algorytmem
        response = message.deepcopy()
        response.swap_sender_receiver()
        response.set_action_type(ActionType.RESPONSE)

        ## zapobiegnij wymianie kluczami z już zalogowanym użytkownikiem (to znaczy już uwierzytelnionym.)
        if message.get_sender() in self.active_users:
            return self.get_error_massage_for_client(message.get_sender(),
                                                     "Not able to exchange keys.")

        if message.get_content_type() == ContentType.PARTIAL_KEY:
            sender_partial_key = message.data
            pair = self.server_account.email, message.get_sender()
            if not pair in self.keys_dict:
                ##gdy DEBUG = False (w pliku socket_settings.) klucz prywatny jest generowany losowo.
                self.keys_dict[pair] = Criptor(self.socket_settings["P"], self.socket_settings["G"], self.DEBUG, 1)
                self.keys_dict[pair].generate_partial_key()
            #wygenerowanie symetrycznego secret key za pomocą wspólnego częściowego klucza.
            self.keys_dict[pair].generate_full_key(sender_partial_key)
            response.data = self.keys_dict[pair].generate_partial_key()
        else:
            return self.get_error_massage_for_client(message.get_sender(),
                                                     "Wrong content type. Require Public Key or Partial key type.")

        return response

    def handle_login(self, message):
        """ Login handler.

        :param message: message from client.
        :return: reponse message with object if exist.
        """
        client = message.data
        query_response = Account.objects. \
            filter(email=client[0], password=client[1])

        client_account = query_response[0] if len(query_response) >= 1 else None
        response = self.get_base_massage_for_client(client_account)

        ##if is already active return response with no account object.
        if client_account.email in self.active_users:
            return self.get_base_massage_for_client(None)

        if client_account is not None:
            try:
                client_account.is_active = True
            except:
                ""

            response.headers['status_code'] = StatusCode.OK
            self.active_users.add(client_account.email)

        return response

    def handle_register(self, message):
        """Register user in database.

        :param message: client message
        :return: response message with object client account if exists
        """
        if message.headers["content_type"] == ContentType.AUTH_TUPLE:
            email = message.data[0]
            password = message.data[1]
            response = self.get_base_massage_for_client()
            exists = True if Account.objects.filter(email=email).first() else False
            if exists:
                response.data = None
                response.headers['status_code'] = StatusCode.USER_EXIST
                response.headers['content-type'] = ContentType.EMPTY

            else:
                new_user = Account(email=email,
                                   username=email,
                                   password=password)
                new_user.save()
                response.data = new_user
                response.headers['status_code'] = StatusCode.OK
                self.active_users.add(email)
            return response

    def handle_check_is_active(self, message):
        """Check if user is active currently

        :rtype: response object
        """
        response = self.get_base_massage_for_client()
        if self.__is_user_active__(message.data):
            response.headers['status_code'] = StatusCode.OK
        response.headers['to'] = message.headers['from_']
        return response

    def __is_user_active__(self, email=None):
        """checking is user active backend

        :param email:
        :return:
        """
        if not email:
            return False
        account = Account.objects.filter(email=email).first()
        if account and account.email in self.active_users:
            return True
        return False

    def handle_logout(self, message):
        """Log out handler

        :param message: message from client
        :return: response message for client
        """
        if message.headers["content_type"] == ContentType.AUTH_TUPLE:
            email = message.data[0]
            response = self.get_base_massage_for_client(email)
            pair = self.server_account.email, message.get_sender()
            account = Account.objects.filter(email=email).first()
            if account:
                account.is_active = False
                account.save()
            if email in self.active_users:
                self.active_users.remove(email)
                self.remove_messages(email)
                self.remove_keys_dict_pair(pair)

                response.headers['status_code'] = StatusCode.OK
            else:
                response.headers['status_code'] = StatusCode.NOTLOGINYET

        else:
            email = ""
            response = self.get_base_massage_for_client(email)
            response.headers['status_code'] = StatusCode.ERROR

        return response

    def handle_send_message(self, message):
        """Funkcja majaca na celu dodanie wiadomosci do dziennika.

        :return: response.
        """
        message_sender = message.get_sender()
        self.append_messages(message)
        response = self.get_base_massage_for_client(message_sender)
        response.headers['status_code'] = StatusCode.OK
        return response

    def handle_download_messages(self, message):
        """Download messages send to sender by user specified in messaga.data

        :param message: message to handle
        :return: response
        """
        if message.headers["content_type"] == ContentType.EMAIL:
            friend_email = message.data
        else:
            raise Exception("Content type must by emial.")

        messages = []
        status_code = StatusCode.OK

        try:
            messages = self.get_messages(message.get_sender(), friend_email)
        except Exception as e:
            status_code = StatusCode.ERROR
        finally:
            response = Message(from_=self.server_account.email,
                               to=message.get_sender(),
                               action_type=ActionType.RESPONSE,
                               data=messages,
                               content_type=ContentType.PLAIN_MESSAGES,
                               status_code=status_code)
        return response

    def load_data(self, data):
        """ load data from bytes

        :rtype: Message
        """

        with self.pickle_lock:
            if b'\r\n\r\n' in data:
                return pickle.loads(data[:-4])
            else:
                return pickle.loads(data)

    def get_base_massage_for_client(self, client=None):
        """Get base message for client.

        :param client: client account or mail
        :return: simple response.
        """
        if isinstance(client, Account):
            client_email = client.email if client else None
            content_type = ContentType.CLIENT_OBJECT
        elif isinstance(client, str):
            client_email = client
            content_type = ContentType.EMAIL
        else:
            client_email = ""
            content_type = ContentType.NONE

        return Message(self.server_account.email, client_email,
                       content_type,
                       ActionType.RESPONSE,
                       'utf-8', StatusCode.NOTFOUND,
                       client)

    def get_error_massage_for_client(self, receiver: str = "",
                                     error_message: str = "",
                                     status_code: StatusCode = StatusCode.ERROR):
        """Get simple error message.

        :param receiver: receiver mail
        :param error_message (str): error message
        :param status_code (StatusCode): status code.
        :return: Simple error message object
        """
        return Message(from_=self.server_account.email, to=receiver,
                       content_type=ContentType.ERROR_MESSAGE,
                       action_type=ActionType.RESPONSE,
                       encoding='utf-8', status_code=status_code,
                       data=error_message)
