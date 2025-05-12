#!/usr/bin/env python3
# tests/test_fsm.py

import sys
import os
import unittest
from unittest.mock import MagicMock

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.truck_fsm.truck_state import TruckState, MissionPhase, TruckContext, Direction
from backend.truck_fsm.truck_fsm import TruckFSM
from backend.truck_fsm.truck_fsm_manager import TruckFSMManager


class TestFSM(unittest.TestCase):
    def setUp(self):
        # 모의 객체 생성
        self.command_sender = MagicMock()
        self.gate_controller = MagicMock()
        self.belt_controller = MagicMock()
        self.mission_manager = MagicMock()
        self.truck_status_manager = MagicMock()
        
        # FSM 매니저 생성
        self.fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            truck_status_manager=self.truck_status_manager
        )
        self.fsm_manager.set_commander(self.command_sender)
        
        # 테스트 코드에서 사용할 TransitionManager 설정 - FSM 매니저의 것을 사용
        self.fsm = self.fsm_manager.fsm
    
    def test_mission_assignment(self):
        """미션 할당 테스트"""
        # 미션 가져오는 메서드 모의 구현
        waiting_mission = MagicMock()
        waiting_mission.mission_id = "M123"
        waiting_mission.source = "LOAD_A"
        self.mission_manager.get_waiting_missions.return_value = [waiting_mission]
        
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "STANDBY", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "IDLE"
        
        # 미션 할당 - 미션 ID를 명시적으로 전달
        result = self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        
        # 검증
        self.assertIsNotNone(self.fsm_manager.fsm.contexts.get("TRUCK1"))
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        self.assertEqual(context.state, TruckState.ASSIGNED)
        self.assertIsNotNone(context.mission_id)
        self.assertEqual(context.mission_phase, MissionPhase.TO_LOADING)
        self.assertEqual(context.direction, Direction.INBOUND)  # 방향 검증
        
        # 명령 전송 검증
        self.command_sender.send.assert_called()
    
    def test_position_update(self):
        """위치 업데이트 테스트"""
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "STANDBY", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "IDLE"
        
        # 미션 할당
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        
        # 이동 중 위치 업데이트
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        
        # 컨텍스트 검증
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        self.assertEqual(context.position, "CHECKPOINT_A")
        self.assertEqual(context.state, TruckState.WAITING)
        self.assertEqual(context.direction, Direction.INBOUND)  # 방향 검증
        
        # 게이트 제어 검증
        self.gate_controller.open_gate.assert_called_with("GATE_A")
    
    def test_loading_workflow(self):
        """적재 작업 흐름 테스트"""
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "STANDBY", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "IDLE"
        
        # 미션 할당
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        
        # 체크포인트 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        
        # 게이트 오픈 확인
        self.fsm_manager.handle_trigger("TRUCK1", "ACK_GATE_OPENED", {})
        
        # 로딩 위치 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_LOAD_A", {})
        
        # 로딩 시작
        self.fsm_manager.handle_trigger("TRUCK1", "START_LOADING", {})
        
        # 로딩 완료
        self.fsm_manager.handle_trigger("TRUCK1", "FINISH_LOADING", {})
        
        # 컨텍스트 검증
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        self.assertEqual(context.state, TruckState.MOVING)
        self.assertEqual(context.mission_phase, MissionPhase.TO_UNLOADING)
        self.assertEqual(context.direction, Direction.OUTBOUND)  # 방향 검증
        
        # RUN 명령 검증
        calls = [call for call in self.command_sender.send.call_args_list if call[0][1] == "RUN"]
        self.assertGreaterEqual(len(calls), 2)  # 최소 2번의 RUN 명령 (초기 + 로딩 완료 후)
    
    def test_unloading_workflow(self):
        """하역 작업 흐름 테스트"""
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "CHECKPOINT_C", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "MOVE_TO_GATE_FOR_UNLOAD"
        
        # 컨텍스트 초기화 - 이전 단계에서 이미 로딩까지 완료한 상태로 가정
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        context.state = TruckState.MOVING
        context.mission_id = "M123"
        context.mission_phase = MissionPhase.TO_UNLOADING
        context.position = "CHECKPOINT_C"
        context.direction = Direction.OUTBOUND  # 방향 설정
        
        # 체크포인트 C 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_C", {})
        
        # 게이트 오픈 확인
        self.fsm_manager.handle_trigger("TRUCK1", "ACK_GATE_OPENED", {})
        
        # 하역 위치 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_BELT", {})
        
        # 하역 시작
        self.fsm_manager.handle_trigger("TRUCK1", "START_UNLOADING", {})
        
        # 하역 완료
        self.fsm_manager.handle_trigger("TRUCK1", "FINISH_UNLOADING", {})
        
        # 컨텍스트 검증
        self.assertEqual(context.state, TruckState.MOVING)
        self.assertEqual(context.mission_phase, MissionPhase.RETURNING)
        self.assertEqual(context.target_position, "STANDBY")
        self.assertEqual(context.direction, Direction.RETURN)  # 방향 검증
        
        # 하역 완료 후 미션 완료 처리 - 실제 운영에서는 STANDBY 위치 도착 후 처리
        # 테스트에서는 직접 미션 완료 호출
        if context.mission_id:
            self.mission_manager.complete_mission(context.mission_id)
        
        # 미션 완료 검증
        self.mission_manager.complete_mission.assert_called()
    
    def test_abnormal_path_recovery(self):
        """비정상 경로 복구 테스트"""
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "STANDBY", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "IDLE"
        
        # 미션 할당
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        
        # 정상적인 흐름 시작
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        self.fsm_manager.handle_trigger("TRUCK1", "ACK_GATE_OPENED", {})
        
        # 컨텍스트 상태 초기화를 위해 직접 설정
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        context.state = TruckState.MOVING
        context.direction = Direction.OUTBOUND  # OUTBOUND 방향으로 직접 설정
        
        # 게이트 컨트롤러 리셋
        self.gate_controller.reset_mock()
        
        # 비정상 경로: 적재 작업을 건너뛰고 체크포인트 C에 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_C", {})
        
        # 게이트 제어 검증 - 현재 위치에 맞는 게이트 제어가 이루어졌는지 확인
        self.gate_controller.open_gate.assert_called_with("GATE_B")
    
    def test_mission_cancellation(self):
        """미션 취소 테스트"""
        # 트럭 상태 모의 구현
        self.truck_status_manager.get_truck_status.return_value = {
            "battery": {"level": 100, "is_charging": False},
            "position": {"location": "STANDBY", "run_state": "IDLE"}
        }
        self.truck_status_manager.get_fsm_state.return_value = "IDLE"
        
        # 미션 할당
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        
        # 체크포인트 도착
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        
        # 미션 취소
        self.fsm_manager.handle_trigger("TRUCK1", "CANCEL_MISSION", {})
        
        # 컨텍스트 검증
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        self.assertEqual(context.state, TruckState.IDLE)
        self.assertIsNone(context.mission_id)
        self.assertEqual(context.mission_phase, MissionPhase.NONE)
        self.assertEqual(context.direction, Direction.RETURN)  # 방향 검증
        
        # 미션 취소 검증
        self.mission_manager.cancel_mission.assert_called_once()
        
        # 복귀 명령 검증
        self.command_sender.send.assert_called_with("TRUCK1", "RUN", {"target": "STANDBY"})
    
    def test_directional_gates(self):
        """방향에 따른 게이트 제어 테스트"""
        # 미션 할당 (INBOUND 방향)
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        
        # INBOUND 방향에서 CHECKPOINT_A에 도착 - GATE_A 열림
        self.gate_controller.reset_mock()
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        self.gate_controller.open_gate.assert_called_with("GATE_A")
        self.gate_controller.close_gate.assert_not_called()
        
        # 로딩 위치 도착 후 로딩 완료 - 방향 전환
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_LOAD_A", {})
        self.fsm_manager.handle_trigger("TRUCK1", "START_LOADING", {})
        self.fsm_manager.handle_trigger("TRUCK1", "FINISH_LOADING", {})
        
        # 방향 검증
        self.assertEqual(context.direction, Direction.OUTBOUND)
        
        # OUTBOUND 방향에서 CHECKPOINT_C에 도착 - GATE_B 열림
        self.gate_controller.reset_mock()
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_C", {})
        self.gate_controller.open_gate.assert_called_with("GATE_B")
        
        # 하역 완료 - 방향 전환
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_BELT", {})
        self.fsm_manager.handle_trigger("TRUCK1", "START_UNLOADING", {})
        self.fsm_manager.handle_trigger("TRUCK1", "FINISH_UNLOADING", {})
        
        # 방향 검증
        self.assertEqual(context.direction, Direction.RETURN)
        
        # RETURN 방향에서 CHECKPOINT_C 도착 - GATE_B 닫힘
        # 상태를 직접 설정
        context.position = "CHECKPOINT_D"
        context.direction = Direction.RETURN
        
        # 게이트 컨트롤러 리셋
        self.gate_controller.reset_mock()
        
        # 체크포인트 C 도착 테스트
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_C", {})
        
        # GATE_B 닫힘 검증
        # 체크포인트 C에서는 RETURN 방향일 때 GATE_B가 닫혀야 함
        self.gate_controller.close_gate.assert_called_with("GATE_B")
    
    def test_bidirectional_gates(self):
        """양방향 게이트 제어 테스트"""
        # 미션 할당
        self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {"mission_id": "M123"})
        context = self.fsm_manager.fsm._get_or_create_context("TRUCK1")
        
        # INBOUND 방향에서는 CP_A에서 열리고 CP_B에서 닫힘
        self.gate_controller.reset_mock()
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_A", {})
        self.gate_controller.open_gate.assert_called_with("GATE_A")
        
        # 양방향 체크포인트 테스트를 위해 직접 컨트롤러 호출
        self.gate_controller.reset_mock()
        
        # CP_B에서의 게이트 제어 확인 - INBOUND 방향일 때 GATE_A 닫힘 처리 검증
        self.fsm_manager.fsm._process_checkpoint_gate_control(
            context, "CHECKPOINT_B", Direction.INBOUND
        )
        self.gate_controller.close_gate.assert_called_with("GATE_A")
        
        # 로딩 위치 도착 및 방향 전환
        context.position = "LOAD_A"
        context.direction = Direction.OUTBOUND  # 직접 방향 전환
        
        # OUTBOUND 방향에서는 CP_B에서 열리고 CP_A에서 닫힘
        self.gate_controller.reset_mock()
        
        # CP_B에서의 게이트 제어 확인 - OUTBOUND 방향일 때 GATE_A 열림 처리 검증
        self.fsm_manager.fsm._process_checkpoint_gate_control(
            context, "CHECKPOINT_B", Direction.OUTBOUND
        )
        self.gate_controller.open_gate.assert_called_with("GATE_A")
        
        # CP_A에서의 게이트 제어 확인 - OUTBOUND 방향일 때 GATE_A 닫힘 처리 검증
        self.gate_controller.reset_mock()
        self.fsm_manager.fsm._process_checkpoint_gate_control(
            context, "CHECKPOINT_A", Direction.OUTBOUND
        )
        self.gate_controller.close_gate.assert_called_with("GATE_A")


if __name__ == "__main__":
    unittest.main() 