#!/usr/bin/env python3
# tests/test_new_fsm.py

import sys
import os
import unittest
from unittest.mock import MagicMock

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.truck_fsm.truck_state import TruckState, MissionPhase, TruckContext
from backend.truck_fsm.state_transition_manager import StateTransitionManager
from backend.truck_fsm.truck_fsm_manager_new import TruckFSMManager


class TestNewFSM(unittest.TestCase):
    def setUp(self):
        # 모의 객체 생성
        self.command_sender = MagicMock()
        self.gate_controller = MagicMock()
        self.belt_controller = MagicMock()
        self.mission_manager = MagicMock()
        self.truck_status_manager = MagicMock()
        
        # 상태 전이 매니저 생성
        self.transition_manager = StateTransitionManager(
            command_sender=self.command_sender,
            gate_controller=self.gate_controller,
            belt_controller=self.belt_controller,
            mission_manager=self.mission_manager
        )
        
        # FSM 매니저 생성
        self.fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            truck_status_manager=self.truck_status_manager
        )
        self.fsm_manager.set_commander(self.command_sender)
    
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
        
        # 미션 할당
        result = self.fsm_manager.handle_trigger("TRUCK1", "ASSIGN_MISSION", {})
        
        # 검증
        self.assertIsNotNone(self.fsm_manager.transition_manager.contexts.get("TRUCK1"))
        context = self.fsm_manager.transition_manager._get_or_create_context("TRUCK1")
        self.assertEqual(context.state, TruckState.ASSIGNED)
        self.assertIsNotNone(context.mission_id)
        self.assertEqual(context.mission_phase, MissionPhase.TO_LOADING)
        
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
        context = self.fsm_manager.transition_manager._get_or_create_context("TRUCK1")
        self.assertEqual(context.position, "CHECKPOINT_A")
        self.assertEqual(context.state, TruckState.WAITING)
        
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
        context = self.fsm_manager.transition_manager._get_or_create_context("TRUCK1")
        self.assertEqual(context.state, TruckState.MOVING)
        self.assertEqual(context.mission_phase, MissionPhase.TO_UNLOADING)
        
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
        context = self.fsm_manager.transition_manager._get_or_create_context("TRUCK1")
        context.state = TruckState.MOVING
        context.mission_id = "M123"
        context.mission_phase = MissionPhase.TO_UNLOADING
        context.position = "CHECKPOINT_C"
        
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
        
        # 비정상 경로: 적재 작업을 건너뛰고 체크포인트 C에 도착
        context = self.fsm_manager.transition_manager._get_or_create_context("TRUCK1")
        prev_state = context.state
        self.fsm_manager.handle_trigger("TRUCK1", "ARRIVED_AT_CHECKPOINT_C", {})
        
        # 컨텍스트 검증 - 시스템이 상태를 적절히 조정했는지 확인
        self.assertNotEqual(context.state, prev_state)  # 상태가 변경되었어야 함
        
        # 게이트 제어 검증 - 현재 위치에 맞는 게이트 제어가 이루어졌는지 확인
        self.gate_controller.open_gate.assert_called_with("GATE_B")


if __name__ == "__main__":
    unittest.main() 