# test_serialio.py

from backend.serialio.serial_manager import SerialManager

# 포트명 = name 으로 넘겨야 FakeSerial에 잘 전달됨
port_map = {
    "GATE_A": "GATE_A",
    "GATE_B": "GATE_B"
}

# FakeSerial 기반 SerialManager 생성
manager = SerialManager(port_map=port_map, use_fake=True)

# 테스트 시퀀스
def test_gate_sequence(facility, action):
    print(f"\n[TEST] {facility} → {action}")
    manager.send_command(facility, action)
    response = manager.read_response(facility)
    print(f"[RESPONSE] {response}")

# GATE_A 테스트
test_gate_sequence("GATE_A", "OPEN")
test_gate_sequence("GATE_A", "CLOSE")

# GATE_B 테스트
test_gate_sequence("GATE_B", "OPEN")
test_gate_sequence("GATE_B", "CLOSE")

# 마무리 정리
manager.close_all()
