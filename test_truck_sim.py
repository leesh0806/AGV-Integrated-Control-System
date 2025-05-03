# test_truck_sim.py
from backend.tcpio.client import TCPClient
import time

truck_id = "TRUCK_001"
client = TCPClient()
client.connect()

def send(cmd, payload={}):
    client.send_command(sender=truck_id, receiver="SERVER", cmd=cmd, payload=payload)
    time.sleep(1)

# 테스트 흐름
send("ASSIGN_MISSION")
send("ARRIVED", {"position": "GATE_A", "gate_id": "GATE_A"})
send("ACK_GATE_OPENED")
send("ARRIVED", {"position": "LOAD_A"})
send("START_LOADING")
send("FINISH_LOADING")
send("ARRIVED", {"position": "GATE_B", "gate_id": "GATE_B"})
send("ACK_GATE_OPENED")
send("ARRIVED", {"position": "BELT"})
send("START_UNLOADING")
send("FINISH_UNLOADING")
send("ARRIVED", {"position": "STANDBY"})
