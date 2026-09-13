"""Navigation Decision Engine: Combines Route, Vision, Safe Path, and Risk into prioritized voice instructions."""
from typing import Dict, Any, Optional
from backend.utils.logger import get_logger

logger = get_logger("NavigationDecisionEngine")

class NavigationState:
    IDLE = "IDLE"
    DESTINATION_SELECTION = "DESTINATION_SELECTION"
    ROUTE_CALCULATION = "ROUTE_CALCULATION"
    NAVIGATING = "NAVIGATING"
    OBSTACLE_DETECTED = "OBSTACLE_DETECTED"
    SAFE_PATH_ANALYSIS = "SAFE_PATH_ANALYSIS"
    PATH_CORRECTION = "PATH_CORRECTION"
    DESTINATION_REACHED = "DESTINATION_REACHED"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ROUTE_DEVIATED = "ROUTE_DEVIATED"

class NavigationDecisionEngine:
    """Combines global routing and local vision obstacle data into priority-ordered voice output."""

    def __init__(self):
        self.state = NavigationState.IDLE
        self.last_spoken_instruction = ""
        self.destination_name = ""
        self._last_primary_obs = None
        self._obs_drop_count = 0

    def process_decision(self, route_status: Dict[str, Any],
                         safe_path_analysis: Dict[str, Any],
                         risk_analysis: Dict[str, Any],
                         gps_status: Dict[str, Any]) -> Dict[str, Any]:
        """Determine current system state and compute highest priority instruction."""
        risk_level = risk_analysis.get("level", "LOW")
        rec_dir = safe_path_analysis.get("recommended_direction", "STRAIGHT")
        primary_obs = safe_path_analysis.get("primary_obstacle")

        # Hysteresis smoothing for obstacle detection to prevent 1-frame drop flickering
        if not primary_obs and self._last_primary_obs and self._obs_drop_count < 3:
            self._obs_drop_count += 1
            primary_obs = self._last_primary_obs
        elif primary_obs:
            self._last_primary_obs = primary_obs
            self._obs_drop_count = 0
        else:
            self._last_primary_obs = None
            self._obs_drop_count = 0

        # 1. State check: Destination reached
        if route_status.get("has_reached_destination"):
            self.state = NavigationState.DESTINATION_REACHED
            return self._build_decision_output(
                priority="HIGH",
                instruction="You have reached your destination.",
                action="STOP",
                state=self.state,
                risk=risk_analysis
            )

        # 2. State check: Route deviated
        if route_status.get("is_deviated"):
            self.state = NavigationState.ROUTE_DEVIATED
            return self._build_decision_output(
                priority="HIGH",
                instruction="You are off route. Recalculating route.",
                action="RECALCULATE",
                state=self.state,
                risk=risk_analysis
            )

        # 3. Priority 1: CRITICAL OBSTACLE (Immediate Stop)
        if risk_level == "CRITICAL" or (primary_obs and primary_obs.get("distance_m", 10.0) <= 1.2):
            self.state = NavigationState.OBSTACLE_DETECTED
            obs_name = primary_obs.get("class", "obstacle") if primary_obs else "obstacle"
            dist = primary_obs.get("distance_m", 0.8) if primary_obs else 0.8
            return self._build_decision_output(
                priority="CRITICAL",
                instruction=f"Stop! {obs_name.capitalize()} directly ahead at {dist} meters.",
                action="STOP",
                state=self.state,
                risk=risk_analysis
            )

        # 4. Priority 2: HIGH RISK OBSTACLE & SAFE PATH CORRECTION
        if risk_level == "HIGH" or rec_dir in ["MOVE LEFT", "MOVE RIGHT", "SLIGHT LEFT", "SLIGHT RIGHT"] or (primary_obs and primary_obs.get("distance_m", 10.0) <= 2.5):
            self.state = NavigationState.PATH_CORRECTION
            obs_name = primary_obs.get("class", "obstacle") if primary_obs else "obstacle"
            dist = primary_obs.get("distance_m", 1.8) if primary_obs else 1.8
            if rec_dir == "MOVE LEFT":
                instruction = f"{obs_name.capitalize()} ahead at {dist} meters. Move slightly left."
            elif rec_dir == "MOVE RIGHT":
                instruction = f"{obs_name.capitalize()} ahead at {dist} meters. Move slightly right."
            elif rec_dir == "SLIGHT LEFT":
                instruction = f"Approaching {obs_name} at {dist} meters. Bear slightly left."
            elif rec_dir == "SLIGHT RIGHT":
                instruction = f"Approaching {obs_name} at {dist} meters. Bear slightly right."
            else:
                instruction = f"Caution. {obs_name.capitalize()} ahead at {dist} meters."

            return self._build_decision_output(
                priority="HIGH",
                instruction=instruction,
                action="CORRECT_PATH",
                state=self.state,
                risk=risk_analysis
            )

        # 5. Priority 3: MEDIUM RISK / NEARBY OBSTACLE DETECTED
        if primary_obs and primary_obs.get("distance_m", 10.0) <= 3.5:
            self.state = NavigationState.OBSTACLE_DETECTED
            obs_name = primary_obs.get("class", "obstacle")
            dist = primary_obs.get("distance_m", 2.8)
            return self._build_decision_output(
                priority="MEDIUM",
                instruction=f"Caution: {obs_name.capitalize()} detected ahead at {dist} meters.",
                action="MONITOR",
                state=self.state,
                risk=risk_analysis
            )

        # 6. Priority 4: TURN INSTRUCTION (from route tracker)
        if route_status.get("is_active"):
            dist_to_turn = route_status.get("distance_to_next_turn", 100.0)
            route_instr = route_status.get("current_instruction", "Walk straight")

            if dist_to_turn <= 20.0 and dist_to_turn > 5.0:
                dist_quantized = int(round(dist_to_turn / 5.0) * 5)
                if "Turn" in route_instr or "Bear" in route_instr:
                    instruction = f"{route_instr} in {dist_quantized} meters."
                else:
                    instruction = f"{route_instr} for {dist_quantized} meters."
            elif dist_to_turn <= 5.0:
                if "Turn" in route_instr or "Bear" in route_instr:
                    instruction = f"{route_instr} now."
                else:
                    instruction = route_instr
            else:
                if "Turn" in route_instr or "Bear" in route_instr:
                    instruction = f"Walk straight. {route_instr} ahead."
                else:
                    instruction = route_instr

            self.state = NavigationState.NAVIGATING
            return self._build_decision_output(
                priority="MEDIUM",
                instruction=instruction,
                action="NAVIGATE",
                state=self.state,
                risk=risk_analysis
            )

        # 7. Default IDLE state
        self.state = NavigationState.IDLE
        return self._build_decision_output(
            priority="LOW",
            instruction="System ready. Say or select a destination to start navigation.",
            action="IDLE",
            state=self.state,
            risk=risk_analysis
        )

    def _build_decision_output(self, priority: str, instruction: str, action: str,
                              state: str, risk: Dict[str, Any]) -> Dict[str, Any]:
        """Package structured decision record."""
        return {
            "priority": priority,
            "instruction": instruction,
            "action": action,
            "state": state,
            "risk_level": risk.get("level", "LOW"),
            "risk_details": risk
        }
