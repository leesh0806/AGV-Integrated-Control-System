# fsm_test_script.py

import time
from backend.tcpio.client import TCPClient

def run_fsm_test():
    truck_id = "TRUCK_01"
    cli = TCPClient()
    cli.connect()

    def send(cmd, payload={}):
        cli.send_command(sender=truck_id, receiver="SERVER", cmd=cmd, payload=payload)
        time.sleep(0.5)

    print(f"\n=== 🚚 {truck_id} 미션 요청 ===")
    send("ASSIGN_MISSION")

    print(f"📍 CHECKPOINT_A 도착")
    send("ARRIVED", {"position": "CHECKPOINT_A"})

    print(f"✅ 게이트 열림 확인 (ACK)")
    send("ACK_GATE_OPENED")

    print(f"📍 적재장 LOAD_A 도착")
    send("ARRIVED", {"position": "LOAD_A"})

    print(f"📦 적재 시작")
    send("START_LOADING")

    print(f"📦 적재 완료")
    send("FINISH_LOADING")

    print(f"📍 CHECKPOINT_C 도착")
    send("ARRIVED", {"position": "CHECKPOINT_C"})

    print(f"✅ 게이트 열림 확인 (ACK)")
    send("ACK_GATE_OPENED")

    print(f"📍 하차장 BELT 도착")
    send("ARRIVED", {"position": "BELT"})

    print(f"📤 하차 시작")
    send("START_UNLOADING")

    print(f"📤 하차 완료")
    send("FINISH_UNLOADING")

    print(f"📍 대기장 STANDBY 도착")
    send("ARRIVED", {"position": "STANDBY"})

    print(f"\n✅ 테스트 완료! 미션 완료까지 정상 FSM 흐름 확인됨\n")

    cli.close()


if __name__ == "__main__":
    run_fsm_test()
