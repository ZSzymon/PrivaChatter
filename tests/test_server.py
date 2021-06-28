from unittest import TestCase

import os
import django
PROJECT_NAME = 'PrivaChatterDjango'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '%s.settings' % PROJECT_NAME)
django.setup()


from server.communication_server import CommunicationServer
from server.models import *
from Client.ClientSide import ClientServer

class TestServer(TestCase):
    def test_server_listen(self):
        server = CommunicationServer()
        server.main_loop()

    def test_AddPerson(self):
        Account.objects.filter(email='test@gmail.com').delete()
        person = Account(email='test@gmail.com',
                         username='szymon',
                         password='test'
                         )
        person.save()
        p = Account.objects.filter(email='test@gmail.com')[0]
        self.assertNotEqual(p, None)
        pass

    def test_serialized_object(self):
        Account.objects.filter(email='test@gmail.com').delete()
        person = Account(email='test@gmail.com',
                         username='szymon',
                         password='test'
                         )
        person.save()
        account = Account.objects.filter(email='test@gmail.com')[0]
        serialized = Account.to_dict(account)
        self.assertTrue(type(serialized) == dict)
        pass

    def test_create_message(self):
        server_account = CommunicationServer().get_server_account()
        client = Account.objects.filter(email='test@gmail.com')[0]
        serialized_account = client.to_dict(client)
        message = Message(server_account.email, client.email,
                          ContentType.CLIENT_OBJECT_AS_DICT,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          serialized_account)
        self.assertIsInstance(message, Message)

    def test_prepare_and_unpack_message(self):
        server_account = CommunicationServer().get_server_account()
        client = Account.objects.filter(email='test@gmail.com')[0]
        serialized_account = client.to_dict(client)
        message = Message(server_account.email, client.email,
                          ContentType.CLIENT_OBJECT_AS_DICT,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          serialized_account)
        raw_message = message.prepare_to_send()
        data = CommunicationServer().load_data(raw_message)
        self.assertEqual(type(data), Message)

        #communication_server.send_message(message)
        #respone = communication_server.get_response()


    def test_handle_login_false(self):
        server = CommunicationServer()
        server_account = server.get_server_account()
        client = Account.objects.filter(email='test@gmail.com')[0]
        message = Message(client.email, server_account.email,
                          ContentType.CLIENT_OBJECT,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          client)

        response = server.handle_login(message)

        self.assertTrue(response.headers['status_code'] == StatusCode.NOT_FOUND)

    def test_handle_login_false(self):
        server = CommunicationServer()
        server_account = server.get_server_account()
        email = 'test@gmail.com'
        password = '3454333'
        message = Message(email, server_account.email,
                          ContentType.AUTH_TUPLE,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          (email, password))
        response = server.handle_login(message)

        self.assertTrue(response.headers['status_code'] == StatusCode.NOTFOUND)

    def test_handle_login_false2(self):
        server = CommunicationServer()
        server_account = server.get_server_account()
        email = 'szymon@gmail.com'
        password = '123456789'
        message = Message(email, server_account.email,
                          ContentType.AUTH_TUPLE,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          (email, password))
        response = server.handle_login(message)

        self.assertTrue(response.headers['status_code'] == StatusCode.NOTFOUND)

