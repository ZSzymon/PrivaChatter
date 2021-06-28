import server.make_stand_alone


def client(to_send_data):
    CRCN = b'\r\n\r\n'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 10000))
        data = to_send_data + CRCN
        s.sendall(data)
        data = b''
        while CRCN not in data:
            data += s.recv(1024)
            print('receving data.')
        if not data:
            print('Error has occered.')

        print('Response:' + data.decode('utf-8'))
        s.close()
    except socket.error:
        print('Connection not established.')
        print(sys.exc_info())


if __name__ == '__main__':
    d = {"Name": 'Szymon',
         "Age": 21}
    msg = pickle.dumps(d)

    client(msg)





class Dupa:
    pass
if __name__ == '__main__':
    main()