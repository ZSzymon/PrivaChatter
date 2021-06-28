import base64
import random
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class Criptor:
    def __init__(self, P, G, debug=False, obj_count=0):
        self.P = P
        self.G = G
        if debug:
            if obj_count == 0:
                self.private_key = 4
            if obj_count == 1:
                self.private_key = 3
        else:
            self.private_key = random.randint(1, 30)
            pass

    @staticmethod
    def fme(x, e, m):
        """Fast modular exponentional. Used for keys exchange algorithm (x^e)%m

        :param x: numer to power
        :param e: power
        :param m: mod
        :return: (x^e)%m
        """
        X = x
        E = e
        Y = 1
        while E > 0:
            if E % 2 == 0:
                X = (X * X) % m
                E = E / 2
            else:
                Y = (X * Y) % m
                E = E - 1
        return Y

    def generate_partial_key(self):
        # self.partial_key = (self.G ** self.private_key) % self.P

        self.partial_key = Criptor.fme(self.G, self.private_key, self.P)
        return self.partial_key

    def __get_key(self, password):
        """Create 256bit key.

        :rtype: b64encoded key
        """
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(password)
        return base64.urlsafe_b64encode(digest.finalize())

    def generate_full_key(self, partial_key_r):
        """Generete secret key.

        :param partial_key_r: partial key of second user
        """
        #secret_key = partial_key_r ** self.private_key
        #secret_key = secret_key % self.P
        secret_key = Criptor.fme(partial_key_r, self.private_key, self.P)
        secret_key = str(secret_key).encode()
        self.secret_key = secret_key
        self.f = Fernet(self.__get_key(secret_key))


    def encrypt_message(self, message):
        """Encrypt message method
        :param message (bytes): Message object
        :rtype: bytes
        """
        return self.f.encrypt(bytes(message))

    def decrypt_message(self, encrypted_message):
        """Decrypt message method
        :param message (bytes): Message object
        :rtype: bytes
        """
        return self.f.decrypt(bytes(encrypted_message))
