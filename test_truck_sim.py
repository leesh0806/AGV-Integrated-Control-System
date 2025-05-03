# test_truck_sim.py

from tcpio.client import TCPClient
import time

TRUCK_ID = "TRUCK_001"
client = TCPClient()
client.connect()

def send(cmd, payload=None, delay=1):
    """서버로 cmd + payload 전송 후 대기"""
    if payload is None:
        payload = {}
    client.send_command(sender=TRUCK_ID, receiver="SERVER", cmd=cmd, payload=payload)
    print(f"[SEND] {cmd} → {payload}")
    time.sleep(delay)

def run_full_mission():
    # 1. 미션 요청
    send("ASSIGN_MISSION")

    # 2. CHECKPOINT_A 도착
    send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"})

    # 3. 게이트 열림 확인
    send("ACK_GATE_OPENED")

    # 4. LOAD_A 도착
    send("ARRIVED", {"position": "LOAD_A"})

    # 5. 적재 시작 / 완료
    send("START_LOADING")
    send("FINISH_LOADING")

    # 6. CHECKPOINT_B 도착
    send("ARRIVED", {"position": "CHECKPOINT_B", "gate_id": "GATE_B"})

    # 7. 게이트 열림 확인
    send("ACK_GATE_OPENED")

    # 8. BELT 도착
    send("ARRIVED", {"position": "BELT"})

    # 9. 하차 시작 / 완료
    send("START_UNLOADING")
    send("FINISH_UNLOADING")

    # 10. STANDBY 도착
    send("ARRIVED", {"position": "STANDBY"})

    print("\n✅ 테스트 완료: 정상 시나리오 흐름 종료\n")

if __name__ == "__main__":
    run_full_mission()
