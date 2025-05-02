from serialio.controller import SerialController
import time

if __name__ == "__main__":
    port_name = "/dev/ttyACM0"  # ⚠️ 아두이노 포트 확인 후 수정
    controller = SerialController(port=port_name, baudrate=9600)

    try:
        print("[Info] 아두이노 연결 대기 중...")
        time.sleep(2)  # 💡 연결 직후 아두이노 리셋 타이밍 대기

        controller.send_command("GATE_A", "OPEN")

        start = time.time()
        while time.time() - start < 5:
            response = controller.read_response()
            if response:
                print("[응답 수신]", response)
                break
        else:
            print("[오류] 아두이노 응답 없음")

    finally:
        controller.close()
