# app.py
import json
from typing import List, Dict, Any, Tuple
import operator
import streamlit as st

# ----------------------------
# 1) Minimal rule engine (same style as lecturer)
# ----------------------------
OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}

# ----------------------------
# Table 1 Rules (Python format - safe)
# ----------------------------
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "name": "Windows open → turn AC off",
        "priority": 100,
        "conditions": [["windows_open", "==", True]],
        "action": {
            "ac_mode": "OFF",
            "fan_speed": "LOW",
            "setpoint": None,
            "reason": "Windows are open",
        },
    },
    {
        "name": "No one home → eco mode",
        "priority": 90,
        "conditions": [["occupancy", "==", "EMPTY"], ["temperature", ">=", 24]],
        "action": {
            "ac_mode": "ECO",
            "fan_speed": "LOW",
            "setpoint": 27,
            "reason": "Home empty; save energy",
        },
    },
    {
        "name": "Too cold → turn off",
        "priority": 85,
        "conditions": [["temperature", "<=", 22]],
        "action": {
            "ac_mode": "OFF",
            "fan_speed": "LOW",
            "setpoint": None,
            "reason": "Already cold",
        },
    },
    {
        "name": "Hot & humid (occupied) → cool strong",
        "priority": 80,
        "conditions": [
            ["occupancy", "==", "OCCUPIED"],
            ["temperature", ">=", 30],
            ["humidity", ">=", 70],
        ],
        "action": {
            "ac_mode": "COOL",
            "fan_speed": "HIGH",
            "setpoint": 23,
            "reason": "Hot and humid",
        },
    },
    {
        "name": "Night (occupied) → sleep mode",
        "priority": 75,
        "conditions": [
            ["occupancy", "==", "OCCUPIED"],
            ["time_of_day", "==", "NIGHT"],
            ["temperature", ">=", 26],
        ],
        "action": {
            "ac_mode": "SLEEP",
            "fan_speed": "LOW",
            "setpoint": 26,
            "reason": "Night comfort",
        },
    },
    {
        "name": "Hot (occupied) → cool",
        "priority": 70,
        "conditions": [["occupancy", "==", "OCCUPIED"], ["temperature", ">=", 28]],
        "action": {
            "ac_mode": "COOL",
            "fan_speed": "MEDIUM",
            "setpoint": 24,
            "reason": "Temperature high",
        },
    },
    {
        "name": "Slightly warm (occupied) → gentle cool",
        "priority": 60,
        "conditions": [
            ["occupancy", "==", "OCCUPIED"],
            ["temperature", ">=", 26],
            ["temperature", "<", 28],
        ],
        "action": {
            "ac_mode": "COOL",
            "fan_speed": "LOW",
            "setpoint": 25,
            "reason": "Slightly warm",
        },
    },
]

DEFAULT_NO_MATCH_ACTION = {
    "ac_mode": "NO_MATCH",
    "fan_speed": "-",
    "setpoint": None,
    "reason": "No rule matched; keep previous / manual setting",
}

def evaluate_condition(facts: Dict[str, Any], cond: List[Any]) -> bool:
    """Evaluate a single condition: [field, op, value]."""
    if len(cond) != 3:
        return False

    field, op, value = cond

    if field not in facts or op not in OPS:
        return False

    try:
        return OPS[op](facts[field], value)
    except Exception:
        return False

def rule_matches(facts: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """All conditions must be true (AND)."""
    return all(evaluate_condition(facts, c) for c in rule.get("conditions", []))

def run_rules(
    facts: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (best_action, fired_rules_sorted)
    best_action chosen by highest priority among fired rules.
    """
    fired = [r for r in rules if rule_matches(facts, r)]

    if not fired:
        return DEFAULT_NO_MATCH_ACTION, []

    fired_sorted = sorted(fired, key=lambda r: r.get("priority", 0), reverse=True)
    best_action = fired_sorted[0].get("action", DEFAULT_NO_MATCH_ACTION)

    return best_action, fired_sorted

# ----------------------------
# 2) Streamlit UI
# ----------------------------
st.set_page_config(page_title="Rule-Based AC Controller", page_icon="❄️", layout="wide")
st.title("Rule-Based Smart Home Air Conditioner Controller")
st.caption("Lecturer-style rule engine + Table 1 rules + priority-based decision output.")

with st.sidebar:
    st.header("Home Facts")

    # Quick-fill button (matches your question example)
    if st.button("Use given facts (temp=22, hum=46, OCCUPIED, NIGHT, windows_open=False)"):
        st.session_state["temperature"] = 22.0
        st.session_state["humidity"] = 46.0
        st.session_state["occupancy"] = "OCCUPIED"
        st.session_state["time_of_day"] = "NIGHT"
        st.session_state["windows_open"] = False

    temperature = st.number_input("Temperature (°C)", value=float(st.session_state.get("temperature", 26.0)))
    humidity = st.number_input("Humidity (%)", value=float(st.session_state.get("humidity", 50.0)))

    occupancy = st.selectbox(
        "Occupancy",
        ["OCCUPIED", "EMPTY"],
        index=0 if st.session_state.get("occupancy", "OCCUPIED") == "OCCUPIED" else 1,
    )

    time_of_day = st.selectbox(
        "Time of day",
        ["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
        index=["MORNING", "AFTERNOON", "EVENING", "NIGHT"].index(st.session_state.get("time_of_day", "MORNING")),
    )

    windows_open = st.checkbox("Windows open", value=bool(st.session_state.get("windows_open", False)))

    st.divider()
    st.header("Rules (JSON)")
    st.caption("You can keep default rules or edit them. Must be valid JSON format.")

    default_json = json.dumps(DEFAULT_RULES, indent=2)
    rules_text = st.text_area("Edit rules here", value=default_json, height=320)

    run = st.button("Evaluate", type="primary")

facts = {
    "temperature": float(temperature),
    "humidity": float(humidity),
    "occupancy": occupancy,
    "time_of_day": time_of_day,
    "windows_open": bool(windows_open),
}

st.subheader("Home Facts")
st.json(facts)

# Parse rules from JSON box (fallback to defaults if invalid)
try:
    rules = json.loads(rules_text)
    assert isinstance(rules, list), "Rules must be a JSON array"
except Exception as e:
    st.error(f"Invalid rules JSON. Using defaults. Details: {e}")
    rules = DEFAULT_RULES

st.subheader("Active Rules")
with st.expander("Show rules", expanded=False):
    st.code(json.dumps(rules, indent=2), language="json")

st.divider()

if run:
    action, fired = run_rules(facts, rules)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("AC Decision (THEN)")
        st.write(f"**AC Mode:** {action.get('ac_mode', '-')}")
        st.write(f"**Fan Speed:** {action.get('fan_speed', '-')}")
        sp = action.get("setpoint", None)
        st.write(f"**Setpoint (°C):** {sp if sp is not None else '-'}")
        st.write(f"**Reason:** {action.get('reason', '-')}")

        if action.get("ac_mode") == "NO_MATCH":
            st.warning("No rule matched. Default action applied.")

    with col2:
        st.subheader("Matched Rules (by priority)")
        if not fired:
            st.info("No rules matched.")
        else:
            for i, r in enumerate(fired, start=1):
                st.write(f"**{i}. {r.get('name','(unnamed)')}** | priority={r.get('priority',0)}")
                st.caption(f"Action: {r.get('action',{})}")
                with st.expander("Conditions"):
                    for cond in r.get("conditions", []):
                        st.code(str(cond))

else:
    st.info("Set input values and click **Evaluate**.")
