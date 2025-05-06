import socket
import json
import time
from backend.serialio.serial_manager import SerialManager
import threading
import requests

# 서버 설정
HOST = '127.0.0.1'
PORT = 8001

manager = SerialManager(port_map={}, use_fake=True)

class TruckSimulator:
    def __init__(self):
        self.source = None
        self.client = None
        self.battery_level = 100
        self.charging = True
        self.current_position = None
        self.connect()

    # TCP 연결
    def connect(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[TCP 연결] {HOST}:{PORT}")
        self.client.connect((HOST, PORT))

    # 메시지 전송
    def send(self, cmd, payload={}, wait=True):
        msg = {
            "sender": "TRUCK_01",
            "receiver": "SERVER",
            "cmd": cmd,
            "payload": payload
        }
        data = json.dumps(msg) + "\n"
        try:
            self.client.send(data.encode())
            print(f"[SEND] {cmd} → {payload}")
            if wait:
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError):
            print("[⚠️ 연결 끊김] 서버에 재연결 시도 중...")
            self.connect()
            self.send(cmd, payload, wait)  # 재시도

    # 미션 수신 대기
    def wait_for_mission_response(self, timeout=5.0):
        self.client.settimeout(timeout)
        try:
            while True:
                # 데이터 수신
                data = self.client.recv(4096)
                if not data:
                    print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                    return False
                raw = data.decode('utf-8').strip()  
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        if msg.get("cmd") == "MISSION_ASSIGNED":
                            self.source = msg["payload"]["source"].upper()
                            print(f"[✅ 미션 수신] → source = {self.source}")
                            return True
                        elif msg.get("cmd") == "NO_MISSION":
                            reason = msg.get("payload", {}).get("reason", "")
                            if reason == "BATTERY_LOW" or reason == "CHARGING":
                                print(f"[🔋 충전 필요] {reason}")
                                # 충전이 완료될 때까지 대기
                                while True:
                                    time.sleep(5)  # 5초마다 배터리 상태 확인
                                    if self.battery_level >= 100:
                                        print("[🔋 충전 완료] 충전 완료 메시지 전송")
                                        self.charging = False
                                        self.send("FINISH_CHARGING", wait=False)
                                        return self.wait_for_mission_response()
                            else:
                                print("[ℹ️ 미션 없음] 서버에서 미션이 없다고 응답함. 3초 후 재요청.")
                                time.sleep(3)
                                self.send("ASSIGN_MISSION", wait=False)
                                # 재귀적으로 다시 대기
                                return self.wait_for_mission_response()
                        elif msg.get("cmd") == "CHARGING_COMPLETED":
                            print("[🔋 충전 완료 메시지 수신]")
                            self.charging = False
                            # 배터리가 30% 이하일 때만 다시 충전 요청
                            if self.battery_level <= 30:
                                print(f"[🔋 배터리 부족] {self.battery_level}% - 충전 요청")
                                self.charging = True
                                self.send("ASSIGN_MISSION", wait=False)
                            else:
                                print(f"[🔋 배터리 충분] {self.battery_level}% - 미션 요청")
                                self.send("ASSIGN_MISSION", wait=False)
                            return self.wait_for_mission_response()
                        elif msg.get("cmd") == "RUN":
                            print("[ℹ️ RUN 명령 수신]")
                            continue
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
            return False
        except socket.timeout:
            print("[⏰ 타임아웃] MISSION_ASSIGNED 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)

    def wait_for_gate_response(self, timeout=5.0):
        self.client.settimeout(timeout)
        try:
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    print("[⏰ 타임아웃] GATE_OPENED 수신 실패")
                    return False

                data = self.client.recv(4096)
                if not data:
                    print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                    return False
                    
                raw = data.decode('utf-8').strip()
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        cmd = msg.get("cmd", "")
                        
                        # GATE_OPENED 명령을 받으면 성공
                        if cmd == "GATE_OPENED":
                            print("[✅ 게이트 열림 확인]")
                            return True
                        
                        # RUN 명령은 무시하고 계속 대기
                        elif cmd == "RUN":
                            continue
                        
                        # GATE_CLOSED는 이전 게이트에 대한 것이므로 무시
                        elif cmd == "GATE_CLOSED":
                            continue
                            
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                            
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
                    
        except socket.timeout:
            print("[⏰ 타임아웃] GATE_OPENED 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)

    def run_full_mission(self):
        while True:
            # ✅ 트럭 등록
            self.send("HELLO", {"msg": "register"}, wait=False)
            time.sleep(0.1)

            # ✅ 상태 초기화 (IDLE로 리셋)
            self.send("RESET", wait=False)
            time.sleep(0.1)

            # ✅ 미션 요청
            self.send("ASSIGN_MISSION", wait=False)
            mission_received = self.wait_for_mission_response()
            if not mission_received:
                print("[ℹ️ 미션 없음] 3초 후 다시 시도합니다.")
                time.sleep(3)
                continue

            try:
                # ✅ 전체 미션 수행
                print("\n[🚛 트럭 이동] CHECKPOINT_A로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"})
                self.current_position = "CHECKPOINT_A"
                self.charging = False
                if self.wait_for_gate_response():
                    self.send("ACK_GATE_OPENED")
                else:
                    print("[❌ 오류] GATE_A가 열리지 않았습니다.")
                    return

                print("\n[🚛 트럭 이동] CHECKPOINT_B로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": "CHECKPOINT_B", "gate_id": "GATE_A"})

                print(f"\n[🚛 트럭 이동] {self.source}로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": self.source})  # load_A or load_B

                print("\n[📦 적재 시작]")
                time.sleep(1)  # 적재 준비 시간
                self.send("START_LOADING")
                time.sleep(3)  # 적재 시간
                self.send("FINISH_LOADING")
                
                print("\n[🚛 트럭 이동] CHECKPOINT_C로 이동 중...")
                time.sleep(2)
                self.send("ARRIVED", {"position": "CHECKPOINT_C", "gate_id": "GATE_B"})
                if self.wait_for_gate_response():
                    self.send("ACK_GATE_OPENED")
                else:
                    print("[❌ 오류] GATE_B가 열리지 않았습니다.")
                    return

                print("\n[🚛 트럭 이동] CHECKPOINT_D로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": "CHECKPOINT_D", "gate_id": "GATE_B"})

                print("\n[🚛 트럭 이동] BELT로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": "BELT"})

                print("\n[📦 하차 시작]")
                time.sleep(1)  # 하차 준비 시간
                self.send("START_UNLOADING")
                time.sleep(3)  # 하차 시간
                self.send("FINISH_UNLOADING")

                print("\n[🚛 트럭 이동] STANDBY로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.send("ARRIVED", {"position": "STANDBY"})
                self.current_position = "STANDBY"
                
                # STANDBY에서는 무조건 충전
                print(f"[🔋 STANDBY 상태] {self.battery_level}% - 충전 시작")
                self.charging = True
                # 충전이 완료될 때까지 대기
                while self.charging:
                    time.sleep(3)
                    if self.battery_level >= 100:
                        print("[🔋 충전 완료] 충전 완료 메시지 전송")
                        self.charging = False
                        self.send("FINISH_CHARGING", wait=False)
                        break

                print("\n✅ 한 턴 완료. 다음 미션을 기다립니다.")
                time.sleep(2)
            except Exception as e:
                print(f"\n❌ 테스트 실패: {e}")
                break

    def report_battery(self, interval=5, drain=5, charge=3):
        while True:
            try:
                # 현재 배터리 레벨 저장
                current_level = self.battery_level
                
                if self.charging:
                    self.battery_level = min(100, self.battery_level + charge)
                    print(f"[DEBUG] 배터리 충전 중: {current_level}% -> {self.battery_level}%")
                elif self.current_position == "STANDBY":
                    # STANDBY에서는 배터리 유지
                    print(f"[DEBUG] STANDBY 상태: 배터리 유지 {self.battery_level}%")
                else:
                    self.battery_level = max(0, self.battery_level - drain)
                    print(f"[DEBUG] 배터리 감소 중: {current_level}% -> {self.battery_level}% (위치: {self.current_position})")
                
                # API로 배터리 상태 전송
                try:
                    print(f"[DEBUG] API로 배터리 상태 전송: {self.battery_level}% (충전중: {self.charging})")
                    response = requests.post(
                        f"http://127.0.0.1:5001/api/truck_battery/TRUCK_01",
                        json={
                            "level": self.battery_level,
                            "is_charging": self.charging
                        }
                    )
                    if response.status_code == 200:
                        print(f"[DEBUG] 배터리 상태 업데이트 성공: {self.battery_level}% (충전중: {self.charging})")
                    else:
                        print(f"[ERROR] 배터리 상태 업데이트 실패: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] 배터리 상태 업데이트 중 오류 발생: {str(e)}")
                    time.sleep(1)  # 오류 발생 시 잠시 대기
                    continue
                
                time.sleep(interval)
            except Exception as e:
                print(f"[ERROR] 배터리 관리 중 오류 발생: {str(e)}")
                time.sleep(1)
                continue

if __name__ == "__main__":
    simulator = TruckSimulator()
    threading.Thread(target=simulator.report_battery, args=(3, 5, 5), daemon=True).start()
    simulator.run_full_mission()
