import serial
import time

def test_belt(port='/dev/ttyACM1', baudrate=9600):
    """
    벨트 모터를 직접 테스트하는 코드입니다.
    """
    try:
        # 시리얼 포트 열기
        ser = serial.Serial(port, baudrate, timeout=2)
        print(f"[성공] {port} 포트에 연결되었습니다.")
        
        # 연결 후 잠시 대기 (아두이노 리셋 시간)
        time.sleep(2)
        
        # 초기 데이터 비우기
        ser.flushInput()
        ser.flushOutput()
        
        while True:
            print("\n===== 벨트 테스트 메뉴 =====")
            print("1. 벨트 켜기 (BELT_RUN)")
            print("2. 벨트 끄기 (BELT_STOP)")
            print("3. 벨트 상태 확인 (BELT_STATUS)")
            print("q. 종료")
            
            cmd = input("명령어 선택: ")
            
            if cmd == 'q':
                break
                
            elif cmd == '1':
                print("[전송] BELT_RUN")
                ser.write(b"BELT_RUN\n")
            
            elif cmd == '2':
                print("[전송] BELT_STOP")
                ser.write(b"BELT_STOP\n")
                
            elif cmd == '3':
                print("[전송] BELT_STATUS")
                ser.write(b"BELT_STATUS\n")
                
            elif cmd == "FINISH_LOADING":
                position = payload.get("position", self.current_position)
                print(f"[✅ 적재 완료 명령 수신] 위치: {position}에서 적재 작업 완료")
                
                # 적재 상태 해제
                self.loading_in_progress = False
                self.loading_finished = True
                
                # 위치 잠금 해제
                if self.position_locked:
                    self.position_locked = False
                    print(f"[🔓 위치 잠금 해제] 위치 잠금이 해제되었습니다. 이제 RUN 명령으로 이동할 수 있습니다.")
                
                # ACK 응답 전송
                self.send("ACK", {"cmd": "FINISH_LOADING", "status": "SUCCESS"}, wait=False)
                return True
                
            else:
                print("[오류] 잘못된 명령어입니다.")
                continue
                
            # 응답 대기 및 출력
            time.sleep(0.5)  # 응답 대기
            
            response = ""
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                response += line + "\n"
                
            if response:
                print(f"[응답]\n{response}")
            else:
                print("[응답 없음] 벨트로부터 응답이 없습니다.")
                
            time.sleep(1)  # 다음 명령 전 대기
            
    except serial.SerialException as e:
        print(f"[오류] 시리얼 포트 연결 실패: {e}")
    finally:
        # 종료 시 포트 닫기
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"[정보] {port} 포트가 닫혔습니다.")

if __name__ == "__main__":
    # 포트 지정 (필요시 변경)
    port = input("시리얼 포트 입력 (기본: /dev/ttyACM1): ") or "/dev/ttyACM1"
    test_belt(port)