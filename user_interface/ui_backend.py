import pathlib
import sys
import os
import logging

from Client.ClientSide import ClientServer

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider,
                             QVBoxLayout, QApplication)
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import time
from _thread import *
import threading

class QTextEditLogger(logging.Handler, QtCore.QObject):
    """Used for debugging purposes. Creating box with logging info.
    """
    appendPlainText = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.resize(200, 400)
        self.appendPlainText.connect(self.widget.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.appendPlainText.emit(msg)




class Ui(QtWidgets.QMainWindow):
    """Main window class
    """
    def __init__(self, debug=False):
        """

        :param debug: specify if debug or not.
        """
        super(Ui, self).__init__()
        dir_path = pathlib.Path(__file__).parent.absolute()
        ui_abs_path = dir_path / "main_window.ui"
        uic.loadUi(ui_abs_path, self)
        self.__init_logout()
        self.debug = debug
        if self.debug:
            self.__init_logging__()
        self.connect_buttons()
        self.__init_widgets__()

        self.client = None


        self.__init_threads()

        self.show()




    def __init_widgets__(self):
        """Initialize all widgets.

        """
        try:
            #self.textBrowser.setText("")
            self.login_widget.show()
            self.register_widget.hide()
            self.register_error_label.hide()
            self.messages_box.hide()
        ##on init remove all data.
        except Exception as e:
            self.handle_logging('info', e)
            stop =1
        self.user_info.hide()


    def mousePressEvent(self, event: QMouseEvent):
        """Po kliknieciu przyciusku myszu resetuje sie czas do wylogowania.

        :param event : Event naciscienia przycisku myszu
        """
        if event.button() == Qt.LeftButton:
            self.update_last_action_time()

    def __init_logout(self):
        """Inicjalizacja metod do autmatycznego logoutu.

        """
        self.logout_after = 360
        self.last_action_lock = allocate_lock()
        self.last_action_time = time.time()
        self.logout_lock = allocate_lock()

    def get_last_action_time(self):
        """Pozyskaj czas ostatniej aktywności

        :return: Ostatni czas ostatniej aktywności
        """
        with self.last_action_lock:
            result = self.last_action_time
        return result

    def update_last_action_time(self):
        """Ustaw czas ostatniej aktynosci na aktualny czas.

        """
        with self.last_action_lock:
            self.last_action_time = time.time()

    def refresh_logout_label(self, each_second):
        """Odswierzanie etykiety wyświetlajacej pozostaly czas do automatycznego wylogowania.

        :param each_second: Co ile sekund ma byc odswierzana etykieta.
        """
        while True:
            if self.client:
                now = time.time()
                last_action = self.get_last_action_time()
                diff = now - last_action
                to_logout = self.logout_after - diff
                self.time_elapsed_to_logout.setText(str(int(to_logout)))
                if to_logout <= 0:
                    self.handle_logout_button()
                self.handle_logging("info", 'refresh.')
            time.sleep(each_second)



    def __init_threads(self):
        """Inicjalizacja workerów. W przyszłości zamienić na QThreads komunikujących się na QSignals oraz QEvents.

        """
        start_new_thread(self.refresh_logout_label, (1,))

    def logged_box(self, email):
        self.user_email_box.setText(email)
        self.user_info.show()

    def connect_buttons(self):
        """Connect button to proper function.
        """

        self.login_button.clicked.connect(self.handle_login_button)
        self.register_button.clicked.connect(self.handle_register_button)
        self.have_account_button.clicked.connect(self.handle_have_account_button)
        self.no_account_button.clicked.connect(self.handle_no_account_button)
        self.logout_button.clicked.connect(self.handle_logout_button)
        self.refresh_button.clicked.connect(self.handle_refresh_button)
        self.send_button.clicked.connect(self.handle_send_message)

    def handle_refresh_message_box(self):
        """Handle reaction of message for clicked refresh button

        """
        receiver = self.friend_email_box.text()
        sender = self.client.client_account.email
        text = self.client.prepare_conversation_with(receiver)

        self.textBrowser.setText(text)

    def handle_refresh_button(self):
        """Refresh message box.

        """
        self.handle_refresh_message_box()

    def __init_logging__(self):
        """Initialize logger.

        """
        self.logging_dict = {
            "info": logging.info,
            "debug": logging.debug,
            "error": logging.error,
            "warning": logging.warning,
        }
        logTextBox = QTextEditLogger(self)
        # log to text box
        logTextBox.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)s %(funcName)s %(message)s\n'))
        logging.getLogger().addHandler(logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)

    def handle_no_account_button(self):
        """Handle no account button

        """
        self.login_widget.hide()
        self.register_widget.show()
        pass

    def handle_have_account_button(self):
        """Handle no account button

        """
        self.register_widget.hide()
        self.login_widget.show()

    def handle_logout_button(self):
        """Handle logout button

        """

        if self.client:
            with self.logout_lock:
                logout_result = self.client.logout()
            self.client = None
        #self.textBrowser.setText("")
        self.__init_widgets__()

    def handle_login_button(self):
        """Handle login button

        """
        login = self.login_box.text()
        password = self.password_box.text()

        if login != "" and password != "":
            try:
                self.client = ClientServer(login, password, auth_now=False)
                self.client.establish_secure_connection(login)
                client_account = self.client.login(login, password)
                login_result = True if client_account else False
                self.handle_logging("info", f"log in with: {login}\n password:{password}\nresult: {login_result}\n")
                if login_result:
                    self.login_widget.hide()
                    self.messages_box.show()
                    self.logged_box(login)
                    self.update_last_action_time()
                self.textBrowser.setText("")
            except Exception as e:
                self.handle_logging('error', f"log in error occered.\nerror: {e}")

    def handle_register_button(self):
        """Register button handling function

        """
        login = self.login_box_2.text()
        password1 = self.password_box_2.text()
        password2 = self.repeat_password_box.text()

        conds = [password1 == password2,
                 len(password1) > 8]
        if all(conds):
            try:
                self.client = ClientServer(login, password1, auth_now=False)
                self.client.establish_secure_connection(login)
                account = self.client.register(login, password1)
                result = True if account else False
                self.handle_logging("info", f"Register: {result}.")
                if result:
                    self.register_error_label.hide()
                    self.register_widget.hide()
                    self.messages_box.show()
                    self.logged_box(account.email)
                else:
                    self.register_error_label.show()

            except Exception as e:
                self.register_error_label.show()
                self.handle_logging("error", f"log in with: {login}\n password:{password}\nresult: {result}\nerror:{e}")
        else:
            result = False
            self.handle_logging("error", f"Register failed.\n")
            self.register_error_label.show()

    def handle_logging(self, level, message):
        if not self.debug:
            return
        self.logging_dict[level](message)

    def handle_send_message(self):
        """Send message from message box to friend.
        """
        receiver = self.friend_email_box.text()
        sender = self.client.client_account.email
        message_text = self.new_message_box.toPlainText()
        if message_text == "":
            return
        self.client.send_message_to_friend(receiver, message_text)
        self.handle_refresh_message_box()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Ui(debug=True)
    app.exec_()


#saperpro@o2.pl
#123456789