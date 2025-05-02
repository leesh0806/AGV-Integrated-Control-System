# gate_test.py

import time
from serialio.serial_manager import SerialManager

if __name__ == "__main__":
    port_map = {
        "GATE_A": "/dev/ttyACM0"  # 실제 연결된 포트로 변경
    }

    manager = SerialManager(port_map)
    gate = "GATE_A"

    try:
        time.sleep(2)
        print(f"[시작] {gate} 열기 명령 전송 중...")
        manager.send_command(gate, "OPEN")
        ack1 = manager.read_response(gate)
        print(f"[응답] {ack1}")

        print("[대기] 1초간 대기 중...")
        time.sleep(1)

        print(f"[시작] {gate} 닫기 명령 전송 중...")
        manager.send_command(gate, "CLOSE")
        ack2 = manager.read_response(gate)
        print(f"[응답] {ack2}")

    finally:
        manager.close_all()
        print("[종료] 시리얼 포트 종료됨")
