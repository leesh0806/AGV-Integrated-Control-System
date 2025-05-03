# backend/run_tcp_server.py

from tcpio.server import TCPServer

if __name__ == "__main__":
    server = TCPServer(port=8000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("[서버 종료 요청]")
        server.stop()