# This is a example file for receiver server
# For Windows OS only work on Python version from 3.9
import os
import dotenv


# Load environment variables from .env file
dotenv.load_dotenv()

import socket
import time
import datetime
import threading


ADAPTER_ADDR = os.getenv("ADAPTER_ADDR")
if not ADAPTER_ADDR:
    print("Please set the ADAPTER_ADDR environment variable in .env file.")
    exit(1)


port = 4  # Normal port for RFCOMM?
buf_size = 1024
keep_alive = True

s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.bind((ADAPTER_ADDR, port))
print("Socket bind to " + ADAPTER_ADDR + " port " + str(port))
s.listen(1)


# Reset keep alive to False every 10 sec
def fun_timer():
    global keep_alive
    keep_alive = False
    global timer

    # Reset timer
    timer = threading.Timer(10, fun_timer)
    timer.start()


timer = threading.Timer(10, fun_timer)
timer.start()


# Reciever
def start_reciever():
    try:
        print("Waiting for connect...")
        client, address = s.accept()
        print(f"Connected to {address}")
        _do_close_ = False
        _do_ack_ = False
        global keep_alive
        keep_alive = True
        global timer

        # Receive data loop
        while True:
            if _do_close_:
                break

            # Tell another device it is okey to send another
            if _do_ack_:
                client.send(b"ACK")
                print("- Send -")
                print(b"ACK")
                _do_ack_ = False
            print("Client listening...")

            while True:
                if keep_alive == False:
                    print("Device has no keep alive message, reset client")
                    _do_close_ = True
                    client.close()
                    break

                data = client.recv(buf_size)
                if data:
                    keep_alive = True
                    timer.cancel()  # Cancel timer
                    print("- Receive -")
                    print(data)

                    # Restart server
                    if data == b"FIN":
                        _do_close_ = True
                        client.close()

                        # Reset timer
                        timer = threading.Timer(10, fun_timer)
                        timer.start()
                        break

                    # Keep alive heartbeat message
                    if data == b"IMA":
                        _do_ack_ = True

                        # Reset timer
                        timer = threading.Timer(10, fun_timer)
                        timer.start()
                        break

                    # Create file
                    if data.startswith(b"STR"):
                        unix_time = str(
                            time.mktime(datetime.datetime.now().timetuple())
                        ).removesuffix(".0")
                        f = open("bipman-" + unix_time + ".png", "wb")

                    # Write file data
                    f.write(data.removeprefix(b"STR").removesuffix(b"EOF"))

                    # Close file
                    if data.endswith(b"EOF"):
                        f.close()
                        _do_ack_ = True

                        # Reset timer
                        timer = threading.Timer(10, fun_timer)
                        timer.start()
                        break

        # Restart
        start_reciever()

    except Exception as e:
        print(f"Error: {e}")
        client.close()

        # Restart
        start_reciever()


start_reciever()
