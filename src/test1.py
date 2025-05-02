import socket
import time

HOST = "192.168.7.57"
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b"RUN\n")  # 또는 b"STOP\n"
    time.sleep(10)
    s.sendall(b"STOP\n")