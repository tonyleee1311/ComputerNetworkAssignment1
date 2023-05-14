import sys
import socket

from ServerWorker import ServerWorker


class Server:

    def main(self):
        # print('Server: def main')
        try:  # Xử lý nhập SERVER_PORT
            SERVER_PORT = int(sys.argv[1])

        except:
            print("[Usage: Server.py Server_port]\n")
        # Khởi tạo ra một socket IPV4 có giao thức TCP
        rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtspSocket.bind(('', SERVER_PORT))  # gắn port = SERVER_PORT cho socket
        rtspSocket.listen(5)  # số lượng kết nối tới socket tối đa là 5
        print("Server is started")
        # Receive client info (address,port) through RTSP/TCP session
        while True:
            clientInfo = {}
            clientInfo['rtspSocket'] = rtspSocket.accept()
            ServerWorker(clientInfo).run()


if __name__ == "__main__":
    (Server()).main()
