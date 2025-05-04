# tests/test_belt_controller.py

import threading
import time
from backend.serialio.controller import SerialController
from backend.serialio.belt_controller import BeltController

def test_belt_controller(use_fake=True):
    port = "BELT_PORT"
    controller = SerialController(port=port, use_fake=use_fake)
    belt = BeltController(serial_controller=controller)

    polling_thread = threading.Thread(target=belt.poll_serial)
    polling_thread.start()

    print("\n[🔧 테스트 시작] 3초 후 BELTACT 명령 전송")
    time.sleep(3)
    belt.send_command("BELTACT")

    print("[🔧 테스트] 10초 후 A_FULL 명령 전송")
    time.sleep(10)
    belt.send_command("A_FULL")

    print("[🔧 테스트] 5초 후 EMRSTOP 명령 전송")
    time.sleep(5)
    belt.send_command("EMRSTOP")

    print("[🧪 테스트 종료까지 5초 대기]")
    time.sleep(5)

    print("[🛑 테스트 종료 요청]")
    belt.running = False        # ✅ 스레드 종료 요청
    controller.close()
    polling_thread.join()       # ✅ 안전 종료 대기

    print("[✅ 테스트 정상 종료됨]")

if __name__ == "__main__":
    test_belt_controller(use_fake=True)
