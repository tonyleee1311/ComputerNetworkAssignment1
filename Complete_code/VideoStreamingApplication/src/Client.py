from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import time
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0  # beginning state
    READY = 1  # ready state
    PLAYING = 2  # playing state
    state = INIT  # the first state

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    checkSocketIsOpen = False
    # checkPlay = False
    counter = 0  # đếm số gói mất
    # Initiation...

    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.counter = 0
        # ---

    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        setupbtn = PhotoImage(file='./Images/settings.png')
        lsetupbtn = Label(image=setupbtn)
        lsetupbtn.image = setupbtn

        self.setup = Button(self.master, bg="#FFFFFF",
                            borderwidth=0,  width=100, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup["image"] = setupbtn
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        playbtn = PhotoImage(file='./Images/play.png')
        lplaybtn = Label(image=playbtn)
        lplaybtn.image = playbtn

        self.start = Button(self.master, bg="#FFFFFF",
                            borderwidth=0, width=100, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start["image"] = playbtn
        self.start["state"] = "disabled"
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button
        pausebtn = PhotoImage(file='./Images/pause.png')
        lpausebtn = Label(image=pausebtn)
        lpausebtn.image = pausebtn

        self.pause = Button(self.master, bg="#FFFFFF",
                            borderwidth=0, width=100, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause["image"] = pausebtn
        self.pause["state"] = "disabled"
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Teardown button
        stopbtn = PhotoImage(file='./Images/stop.png')
        lstopbtn = Label(image=stopbtn)
        lstopbtn.image = stopbtn

        self.teardown = Button(self.master, bg="#FFFFFF",
                               borderwidth=0, width=100, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown["image"] = stopbtn
        self.teardown["state"] = "disabled"
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, bg="#FFFFFF", height=19)
        self.label.grid(row=0, column=0, columnspan=4,
                        sticky=W + E + N + S, padx=5, pady=5)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)
            self.start["state"] = "normal"

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        for i in os.listdir():
            if i.find(CACHE_FILE_NAME) == 0:
                os.remove(i)
        time.sleep(1)
        self.state = self.INIT
        # self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0
        self.counter = 0
        # self.checkPlay = False
        self.connectToServer()
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.label.pack_forget()
        self.label.image = ''
        self.pause["state"] = "disabled"
        self.start["state"] = "disabled"
        self.teardown["state"] = "disabled"

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # self.checkPlay = True
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)
            self.pause["state"] = "normal"
            self.teardown["state"] = "normal"

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                currFrameNbr = rtpPacket.seqNum()
                print("Current Seq Num: " + str(currFrameNbr))

                if currFrameNbr > self.frameNbr:  # Discard the late packet
                    self.frameNbr = currFrameNbr
                    self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                    # Upon receiving ACK for TEARDOWN request,
                    # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning(
                'Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------

        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "SETUP %s RTSP/1.0\nCSeq: %d\nTRANSPORT: RTP/UDP; client_port= %d" % (
                self.fileName, self.rtspSeq, self.rtpPort)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PLAY %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PLAY
        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PAUSE %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PAUSE
        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "TEARDOWN %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.TEARDOWN
        else:
            return

        # Send the RTSP request using rtspSocket.
        # ...
        self.rtspSocket.send(request.encode())
        print('\n Data sent:\n' + request)

    def recvRtspReply(self):
        # print('Client: def recvRtspReply')
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)  # 1024 bytes

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split(
            '\n')  # lines là list chứa các string trả về từ server
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        # -------------
                        # TO COMPLETE
                        # -------------
                        # Update RTSP state.
                        # self.state = ...
                        self.state = self.READY
                        self.displayNoti()
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        # self.state = ...
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        # self.state = ...
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()

                    elif self.requestSent == self.TEARDOWN:
                        # self.state = ...
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...
        self.checkSocketIsOpen = True
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket.settimeout(0.5)
        try:
            # Bind the socket to the address using the RTP port given by the client user
            # ...
            # self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
        except:
            tkinter.messagebox.showwarning(
                'Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Close?", "Do you want to close the program?"):
            if self.state != self.TEARDOWN:
                self.sendRtspRequest(self.TEARDOWN)
            if (self.checkSocketIsOpen):
                self.rtpSocket.shutdown(socket.SHUT_RDWR)
                self.rtpSocket.close()
            self.master.destroy()  # Close the gui window
            sys.exit(0)

    def displayNoti(self):
        top = Toplevel()
        top.configure(bg="#FFFFFF")
        top.iconbitmap(r'logo.ico')
        top.title("Notification")
        top.geometry('300x200')
        Lb1 = Listbox(top, width=80, height=20)
        Lb1.insert(1, "Video loaded and ready to play ")
        Lb1.insert(2, "Name Video: " + str(self.fileName))
        Lb1.pack()
