from server.communication_server import CommunicationServer

def main():
    server = CommunicationServer()
    server.main_loop()


if __name__ == '__main__':
    main()


