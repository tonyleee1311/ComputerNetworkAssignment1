import sys
from tkinter import Tk
from Client import Client
from Client2 import Client2
if __name__ == "__main__":
    try:
        serverAddr = sys.argv[1]
        serverPort = sys.argv[2]
        rtpPort = sys.argv[3]
        fileName = sys.argv[4]
    except:
        print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")

    # Create a new client
    print('Normal Option: 1')
    print('Extend Option: 2')
    while True:
        INPUT = int(input('Your choice: '))
        if (INPUT == 1):
            root = Tk()
            app = Client(root, serverAddr, serverPort, rtpPort, fileName)
            break
        elif (INPUT == 2):
            root = Tk()
            app = Client2(root, serverAddr, serverPort, rtpPort, fileName)
            break

        else:
            print('Please enter 1 or 2 only: ')
    app.master.title("Media Player (MP)")
    app.master.configure(bg="#FFF")
    app.master.iconbitmap(r'logo.ico')
    root.mainloop()

