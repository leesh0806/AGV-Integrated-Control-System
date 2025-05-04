import socket
import json
import time

# 서버 설정
HOST = '127.0.0.1'
PORT = 8001

class TruckSimulator:
    def __init__(self):
        self.source = None
        self.client = None
        self.connect()

    def connect(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[TCP 연결] {HOST}:{PORT}")
        self.client.connect((HOST, PORT))

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

    def wait_for_mission_response(self, timeout=5.0):
        self.client.settimeout(timeout)
        try:
            while True:
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
            while True:
                data = self.client.recv(4096)
                if not data:
                    print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                    return False
                    
                raw = data.decode('utf-8').strip()
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        if msg.get("cmd") == "GATE_OPENED":
                            print("[✅ 게이트 열림 확인]")
                            return True
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
            return False
        except socket.timeout:
            print("[⏰ 타임아웃] GATE_OPENED 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)

    def run_full_mission(self):
        # ✅ 트럭 등록
        self.send("HELLO", {"msg": "register"}, wait=False)
        time.sleep(0.1)

        # ✅ 상태 초기화 (IDLE로 리셋)
        self.send("RESET", wait=False)
        time.sleep(0.1)

        # ✅ 미션 요청
        self.send("ASSIGN_MISSION", wait=False)
        if not self.wait_for_mission_response():
            return

        try:
            # ✅ 전체 미션 수행
            print("\n[🚛 트럭 이동] CHECKPOINT_A로 이동 중...")
            time.sleep(2)  # 이동 시간
            self.send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"})
            if self.wait_for_gate_response():
                self.send("ACK_GATE_OPENED")
            else:
                print("[❌ 오류] GATE_A가 열리지 않았습니다.")
                return

            print("\n[🚛 트럭 이동] CHECKPOINT_B로 이동 중...")
            time.sleep(2)  # 이동 시간
            self.send("ARRIVED", {"position": "CHECKPOINT_B", "gate_id": "GATE_A"})

            print("\n[🚛 트럭 이동] LOAD_A로 이동 중...")
            time.sleep(2)  # 이동 시간
            self.send("ARRIVED", {"position": self.source})  # load_A or load_B

            print("\n[📦 적재 시작]")
            time.sleep(1)  # 적재 준비 시간
            self.send("START_LOADING")
            time.sleep(3)  # 적재 시간
            self.send("FINISH_LOADING")
            
            print("\n[🚛 트럭 이동] CHECKPOINT_C로 이동 중...")
            time.sleep(2)  # 이동 시간
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

            print("\n✅ 테스트 완료: 정상 시나리오 흐름 종료")
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
        finally:
            self.client.close()

if __name__ == "__main__":
    simulator = TruckSimulator()
    simulator.run_full_mission()
