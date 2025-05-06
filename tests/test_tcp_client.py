# backend/test_tcp_client

from backend.tcpio.client import TCPClient
import time

if __name__ == "__main__":
    client = TCPClient(host="127.0.0.1", port=8000)
    client.connect()
    client.send_command(
        sender="TRUCK01",
        receiver="SERVER",
        cmd="OBSTACLE",
        payload={
            "detected": "DETECTED",
            "position": "checkpoint_A",
            "distance_cm": "10",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    )
    response = client.read_response()
    client.close()