from unittest import TestCase

import os
import django
from cryptography.fernet import Fernet
PROJECT_NAME = 'PrivaChatterDjango'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '%s.settings' % PROJECT_NAME)
django.setup()

from server.communication_server import CommunicationServer
from server.models import *
from server.criptor import Criptor
from server.ClientSide import ClientServer
from server.tools import *
class TestClientSide(TestCase):
    def test_register_positive(self):
        email = "deletetest@gmail.com"
        password = "superlongpassword!@#"
        Account.objects.filter(email=email).delete()
        client = ClientServer(email, password, True, False)
        account = client.register(email, password)
        self.assertIsNotNone(account)
        self.assertIsInstance(account, Account)

    def test_register_negative(self):
        email = "szymon@gmail.com"
        password = "superlongpassword!@#"
        Account(email=email, password=password).save()
        client = ClientServer(email, password, True, False)
        account = client.register(email, password)
        Account.objects.filter(email=email).delete()
        self.assertIsNone(account)

    def test_login_positive(self):
        login_result = ClientServer(auth_now=False).login("test@gmail.com", "zaq1@WSX")
        self.assertIsNotNone(login_result)
        self.assertTrue(login_result.email == "test@gmail.com")
        pass


    def test_login_false(self):
        login_result = ClientServer(auth_now=False).login("test@gmail.com", "za4t3q1@WSX")
        stop = 1
        self.assertIsNone(login_result)

    def test_default_login(self):
        login_result = ClientServer().login()
        self.assertIsNotNone(login_result)
        pass

    def test_check_is_active_true(self):
        client = ClientServer()
        login_result = client.login()
        self.assertIsNotNone(login_result)
        is_active = client.is_friend_active("test2@gmail.com")
        self.assertTrue(is_active)
        pass

    def test_check_is_active_false(self):
        client = ClientServer(auth_now=False)
        friend_email = "jacek6342@gmail.com"
        login_result = client.login()
        self.assertTrue(login_result)
        is_active = client.is_friend_active(friend_email)
        self.assertFalse(is_active)
        pass

    def test_logout_true(self):
        client = ClientServer()
        login_result = client.login()
        self.assertTrue(login_result)
        logout_result = client.logout()
        self.assertTrue(logout_result)

    def test_logout_false(self):
        client = ClientServer(auth_now=False)
        logout_result = client.logout()
        self.assertTrue(logout_result)

    def test_send_message_to_friend(self):
        client = ClientServer("test@gmail.com", "zaq1@WSX", auth_now=True)
        friend_emial = "test@gmail.com"
        string_message = "This is test message"
        response = client.send_message_to_friend(friend_emial, string_message)
        self.assertTrue(response)
        pass

    #def test_download_message_true(self):
    #    client = ClientServer("test@gmail.com", "zaq1@WSX")
    #    friend_emial = "test@gmail.com"
    #    string_message = "This is test message"
    #    response = client.send_message_to_friend(friend_emial, string_message)
    #    self.assertTrue(response)
    #    messages = client.download_message_from_friend(friend_emial)
    #    self.assertTrue(len(client.messages[friend_emial]) > 0)
    #    pass
    #def test_download_message_false(self):
    #    client = ClientServer("test@gmail.com", "zaq1@WSX")
    #    friend_emial = "test@gmail.com"
    #    string_message = "This is test message"
    #    response = client.send_message_to_friend(friend_emial, string_message)
    #    self.assertTrue(response)
    #    client.download_message_from_friend(friend_emial+"345")
    #    self.assertFalse(len(client.messages[friend_emial]) > 0)
    #    pass

    def test_login_to_people(self):
        message_str = "Hi there give me answers to PAS Exam."
        sender_mail, sender_password = "test@gmail.com", "zaq1@WSX"
        receiver_mail, receiver_password = "jacek@gmail.com", "12345678"
        sender = ClientServer(sender_mail, sender_password).login(sender_mail, sender_password)
        receiver = ClientServer(sender_mail, sender_password).login(receiver_mail, receiver_password)

        self.assertIsInstance(sender, Account)
        self.assertIsInstance(receiver, Account)

    def test_send_recive_two_clients(self):
        message_str = "Hi there give me answers to PAS Exam."
        sender_mail, sender_password  = "test@gmail.com" , "zaq1@WSX"
        receiver_mail, receiver_password  = "jacek@gmail.com", "12345678"
        sender = ClientServer(sender_mail, sender_password)
        receiver = ClientServer(receiver_mail, receiver_password)
        self.assertTrue(sender.is_login())
        self.assertTrue(receiver.is_login())

        sender.send_message_to_friend(receiver_mail, message_str)
        receiver.download_message_from_friend(receiver_mail)
        messages = receiver.get_messages(sender_mail)
        self.assertTrue(len(messages) > 0)

        pass

    def test_download_public_keys(self):
        client = ClientServer("test@gmail.com", "zaq1@WSX")
        client.download_public_keys_server("test@gmail.com")
        self.assertTrue((client.client_account.email, client.get_server_email()) in client.keys_dict)

    def test_exchange_private_keys(self):
        client = ClientServer("test@gmail.com", "zaq1@WSX")
        client.download_public_keys_server("test@gmail.com")
        client.exchange_partial_keys_server("test@gmail.com")

        self.assertTrue((client.client_account.email, client.get_server_email()) in client.keys_dict)

    def test_encrypt_decrypt(self):
        message = Message("sender_mail", "receiver_mail",
                          ContentType.EMPTY,
                          ActionType.LOGIN,
                          'utf-8', 200,
                          "Some data string")
        raw_message = message.prepare_to_send()
        
        cripter = Criptor(23,9,True, 1)
        cripter.generate_partial_key()
        cripter.generate_full_key(7)
        
        encrypted = cripter.encrypt_message(raw_message)
        decrypted = cripter.decrypt_message(encrypted)
        self.assertTrue(raw_message == decrypted)

    def test_encrypted_message(self):
        login = "test@gmail.com"
        password = "zaq1@WSX"
        client = ClientServer(login, password, auth_now=False)
        client.establish_secure_connection(login)
        result = client.login(login, password)
        self.assertTrue(result)
        #login_result = client.login("test@gmail.com", "zaq1@WSX")
        #self.assertIsNotNone(login_result)

        pass

    def test_send_recive_two_clients_encrypted(self):
        message_str = "Hi there give me answers to PAS Exam."
        sender_mail, sender_password  = "test@gmail.com" , "zaq1@WSX"
        receiver_mail, receiver_password  = "jacek@gmail.com", "12345678"
        sender = ClientServer(sender_mail, sender_password,auth_now=False)
        receiver = ClientServer(receiver_mail, receiver_password, auth_now=False)
        self.assertFalse(sender.is_login())
        self.assertFalse(receiver.is_login())

        sender.login(sender_mail, sender_password)
        receiver.login(receiver_mail, receiver_password)
        self.assertTrue(sender.is_login())
        self.assertTrue(receiver.is_login())

        sender.send_message_to_friend(receiver_mail, message_str)
        receiver.download_message_from_friend(receiver_mail)
        messages = receiver.get_messages(sender_mail)

        self.assertTrue(len(messages) > 0)


        pass


    def test_send_message_to_friend_encrypted(self):
        client = ClientServer("test@gmail.com", "zaq1@WSX", auth_now=False)
        client.establish_secure_connection("test@gmail.com")
        client.login("test@gmail.com","zaq1@WSX")
        friend_emial = "test@gmail.com"
        string_message = "This is test message"
        response = client.send_message_to_friend(friend_emial, string_message)
        self.assertTrue(response)
        pass
    
    def test_encrypted_conversation(self):
        u1, p1 = "test@gmail.com", "zaq1@WSX"
        u2, p2 = "saperpro@o2.pl", "123456789"
        client1 = ClientServer(u1, p1, auth_now=False)
        client1.establish_secure_connection(u1)
        client1.login(u1, p1)
        
        client2 = ClientServer(u2, p2, auth_now=False)
        client2.establish_secure_connection(u2)
        client2.login(u2, p2)
        
        client1.send_message_to_friend(u2, "Hi saper")
        client1.send_message_to_friend(u2, "How are you")
        client2.send_message_to_friend(u1, "hi test, i'm fine and you")
        client1.send_message_to_friend(u2, "thanks fine. ")
        
        client2.download_message_from_friend(u1)
        c2_messages = client2.get_messages(u1)
        
        text = client1.prepare_conversation_with(u2)
        self.assertTrue(text)
        pass