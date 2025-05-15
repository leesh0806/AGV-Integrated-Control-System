#!/usr/bin/env python3
import serial
import time
import argparse
import os
import sys

def test_belt_cds(port='/dev/ttyACM1', baudrate=9600, duration=60):
    """벨트 컨베이어의 CDS 센서 값을 모니터링하는 테스트 코드"""
    try:
        # 시리얼 포트 열기
        print(f"[연결] {port}에 연결 시도 중...")
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"[성공] {port}에 연결되었습니다.")
        
        # 연결 후 잠시 대기 (아두이노 리셋 시간)
        time.sleep(2)
        
        # 초기 데이터 비우기
        ser.flushInput()
        ser.flushOutput()
        
        # 대화형 모드 시작
        print("\n===== 벨트 CDS 센서 테스트 =====")
        print("명령어 목록:")
        print("  1. 'cds' - 현재 CDS 센서 값 요청")
        print("  2. 'debug_on' - 디버그 모드 켜기 (자동 값 출력)")
        print("  3. 'debug_off' - 디버그 모드 끄기")
        print("  4. 'calibrate' - CDS 센서 자동 보정")
        print("  5. 'run' - 벨트 작동 시작")
        print("  6. 'stop' - 벨트 정지")
        print("  7. 'q' - 종료")
        print("=====================================")
        
        # 시리얼 모니터링 및 명령 처리 루프
        while True:
            # 사용자 입력 확인
            cmd = input("\n명령 입력> ")
            
            # 숫자 입력 처리 추가
            if cmd == '1':
                cmd = 'cds'
            elif cmd == '2':
                cmd = 'debug_on'
            elif cmd == '3':
                cmd = 'debug_off'
            elif cmd == '4':
                cmd = 'calibrate'
            elif cmd == '5':
                cmd = 'run'
            elif cmd == '6':
                cmd = 'stop'
            elif cmd == '7':
                cmd = 'q'
                
            if cmd.lower() == 'q':
                print("[종료] 프로그램을 종료합니다.")
                break
                
            elif cmd.lower() == 'cds':
                print("[명령] CDS 센서 값 요청")
                ser.write(b"CDS_VALUE\n")
                
            elif cmd.lower() == 'debug_on':
                print("[명령] 디버그 모드 켜기")
                ser.write(b"DEBUG_ON\n")
                
            elif cmd.lower() == 'debug_off':
                print("[명령] 디버그 모드 끄기")
                ser.write(b"DEBUG_OFF\n")
                
            elif cmd.lower() == 'calibrate':
                print("[명령] 센서 자동 보정 시작 (약 5초 소요)")
                ser.write(b"CALIBRATE\n")
                
            elif cmd.lower() == 'run':
                print("[명령] 벨트 작동 시작")
                ser.write(b"BELT_RUN\n")
                
            elif cmd.lower() == 'stop':
                print("[명령] 벨트 정지")
                ser.write(b"BELT_STOP\n")
                
            else:
                print(f"[알림] 알 수 없는 명령: {cmd}")
                continue

            # 명령 후 응답 대기 및 출력 (1초간)
            timeout = time.time() + 3  # 3초 타임아웃
            while time.time() < timeout:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            # CDS 값 응답 형식화
                            if "CDS_VALUE" in line:
                                parts = line.split(",")
                                print("\n[CDS 센서 값]")
                                for part in parts:
                                    print(f"  {part}")
                                print()
                            else:
                                print(f"[응답] {line}")
                    except UnicodeDecodeError:
                        print("[오류] 응답 디코딩 실패")
                time.sleep(0.1)
                
    except serial.SerialException as e:
        print(f"[오류] 시리얼 포트 연결 실패: {e}")
    except KeyboardInterrupt:
        print("\n[종료] 사용자가 종료했습니다.")
    finally:
        # 종료 시 포트 닫기
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"[정보] {port} 포트가 닫혔습니다.")

def find_arduino_ports():
    """시스템에서 사용 가능한 아두이노 포트 목록 반환"""
    import serial.tools.list_ports
    
    ports = list(serial.tools.list_ports.comports())
    arduino_ports = []
    
    for p in ports:
        # Arduino나 USB 포트 찾기
        if 'ACM' in p.device or 'Arduino' in p.description or 'USB' in p.description:
            arduino_ports.append(p.device)
    
    return arduino_ports

if __name__ == "__main__":
    # 명령행 인자 처리
    parser = argparse.ArgumentParser(description='벨트 컨베이어 CDS 센서 테스트')
    parser.add_argument('-p', '--port', help='시리얼 포트 지정 (예: /dev/ttyACM1)')
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help='통신 속도 (기본: 9600)')
    
    args = parser.parse_args()
    port = args.port
    
    # 포트가 지정되지 않았으면 자동 탐색
    if not port:
        available_ports = find_arduino_ports()
        
        if not available_ports:
            print("[오류] 연결된 아두이노를 찾을 수 없습니다.")
            sys.exit(1)
        
        if len(available_ports) == 1:
            port = available_ports[0]
            print(f"[자동 감지] 아두이노 포트: {port}")
        else:
            print("[선택] 여러 포트가 감지되었습니다:")
            for i, p in enumerate(available_ports):
                print(f"  {i+1}: {p}")
            
            selection = input("사용할 포트 번호를 입력하세요: ")
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(available_ports):
                    port = available_ports[idx]
                else:
                    print("[오류] 잘못된 선택입니다.")
                    sys.exit(1)
            except ValueError:
                print("[오류] 숫자를 입력해야 합니다.")
                sys.exit(1)
    
    test_belt_cds(port, args.baudrate) 