import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import requests

# Hardcoded to avoid import warnings
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"

st.set_page_config(page_title="Mashreq Social Signal Dashboard", layout="wide")

# Load risks data
@st.cache_data
def load_risks():
    try:
        with open("../output/risks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure confidence is a float
            for risk in data:
                if isinstance(risk.get('confidence'), str):
                    risk['confidence'] = float(risk['confidence'])
            return data
    except FileNotFoundError:
        st.error("❌ risks.json not found. Run agent.py first.")
        return []
    except Exception as e:
        st.error(f"❌ Error loading risks: {e}")
        return []

def generate_escalation_options(summary: str, risk_type: str, risk_level: str):
    """Generate AI-powered escalation options."""
    prompt = f"""
You are a bank risk response assistant.
Given the risk summary, generate EXACTLY 3 concise action options to address it.
Return ONLY valid JSON in this format:
{{
  "options": ["option 1", "option 2", "option 3"]
}}

Risk Type: {risk_type}
Risk Level: {risk_level}
Summary: {summary}
"""
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        raw_text = response.json()["response"].strip()
        # Simple JSON extraction
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end != 0:
            data = json.loads(raw_text[start:end])
            options = data.get("options", [])
            return [str(o).strip() for o in options][:3]
    except:
        pass
    return ["Monitor virality", "Prepare statement", "Contact affected parties"]

def show_confidence_meter(confidence):
    """Display a visual confidence meter."""
    st.write("**Confidence Level**")
    
    # Color coding
    if confidence >= 0.7:
        color = "🟢"
        label = "High Confidence"
        bar_color = "#28a745"
    elif confidence >= 0.4:
        color = "🟡"
        label = "Medium Confidence"
        bar_color = "#ffc107"
    else:
        color = "🔴"
        label = "Low Confidence"
        bar_color = "#dc3545"
    
    st.markdown(f"### {color} {confidence:.0%} - {label}")
    st.progress(confidence)

def chat_sidebar(risk):
    """Sidebar chatbot for risk Q&A."""
    st.sidebar.header("💬 Risk Assistant")
    st.sidebar.write("Ask questions about this risk")
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    chat_container = st.sidebar.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.write(f"**You:** {msg['content']}")
            else:
                st.write(f"**Assistant:** {msg['content']}")
    
    # Chat input and button in sidebar
    col1, col2 = st.sidebar.columns([4, 1])
    with col1:
        user_input = st.text_input("Your question:", key=f"chat_input_{risk['post_id']}")
    with col2:
        send = st.button("Send", key=f"send_btn_{risk['post_id']}")
    
    if send and user_input.strip():
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        prompt = f"""
You are a bank risk analyst assistant. Answer user questions about the risk.
Keep answers concise and grounded in the provided context.

Caption: {risk['caption']}
Risk Type: {risk['risk_type']}
Risk Level: {risk['risk_level']}
Confidence: {risk['confidence']}
Department: {risk['department']}
Why It Matters: {risk['why_it_matters']}
Summary: {risk['summary']}

User Question: {user_input}
"""
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        try:
            with st.spinner("Assistant is thinking..."):
                response = requests.post(OLLAMA_URL, json=payload, timeout=30)
                response.raise_for_status()
                answer = response.json()["response"].strip()
                st.session_state.chat_history.append({'role': 'assistant', 'content': answer})
        except requests.exceptions.Timeout:
            st.session_state.chat_history.append({'role': 'assistant', 'content': "⏱️ Request timeout. Please try again."})
        except Exception as e:
            st.session_state.chat_history.append({'role': 'assistant', 'content': f"❌ Error: {str(e)}"})
        
        st.rerun()
    
    if st.sidebar.button("Clear Chat", key=f"clear_chat_{risk['post_id']}"):
        st.session_state.chat_history = []
        st.rerun()

def show_risk_detail(risk, risks_list):
    """Detailed risk view with enhanced UI."""
    
    # Always show chat sidebar if "Other" was clicked
    if st.session_state.get('show_chat', False):
        chat_sidebar(risk)
    
    # Risk Title
    st.title(f"🚨 {risk['risk_type'].replace('_', ' ').title()}")
    
    # Status badge
    status = risk.get('status', 'pending')
    status_colors = {
        'pending': '🟠',
        'monitoring': '🔵',
        'validation_requested': '🟣',
        'flagged': '🟡',
        'dismissed': '⚫',
        'actioned': '🟢'
    }
    st.markdown(f"### Status: {status_colors.get(status, '⚪')} {status.replace('_', ' ').title()}")
    
    st.divider()
    
    # Main info in columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Risk Description")
        st.write(risk['summary'])
        
        st.subheader("💡 Why It Matters")
        st.write(risk['why_it_matters'])
        
        st.subheader("📝 Original Caption")
        st.info(risk['caption'])
        
        st.write(f"**Department:** {risk['department']}")
        st.write(f"**Detected:** {risk['time-detected']}")
    
    with col2:
        show_confidence_meter(risk['confidence'])
        
        st.metric("Risk Level", risk['risk_level'].upper())
    
    st.divider()
    
    # Action Buttons
    st.subheader("⚡ Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Escalate", use_container_width=True, type="primary"):
            st.session_state.show_escalation = True
            st.session_state.escalation_risk = risk
            st.rerun()
    
    with col2:
        if st.button("🗑️ Dismiss", use_container_width=True):
            risk['action'] = 'dismiss'
            risk['status'] = 'dismissed'
            risk['reviewed_at'] = datetime.utcnow().isoformat()
            save_risk_action(risk)
            st.success("✅ Risk dismissed")
            st.session_state.selected_risk = None
            st.rerun()
    
    with col3:
        if st.button("💬 Other (Chat)", use_container_width=True):
            st.session_state.show_chat = True
            st.rerun()
    
    # Escalation Modal
    if st.session_state.get('show_escalation', False):
        show_escalation_modal(risk)
    
    # Back button
    if st.button("← Back to Dashboard"):
        st.session_state.selected_risk = None
        st.session_state.show_escalation = False
        st.session_state.show_chat = False
        st.session_state.chat_history = []
        st.rerun()

def show_escalation_modal(risk):
    """Show escalation options in a modal-style container."""
    st.markdown("---")
    st.subheader("🚀 Escalation Options")
    
    # Generate options
    if 'escalation_options' not in st.session_state:
        with st.spinner("Generating mitigation options..."):
            options = generate_escalation_options(
                risk['summary'],
                risk['risk_type'],
                risk['risk_level']
            )
            st.session_state.escalation_options = options
    else:
        options = st.session_state.escalation_options
    
    st.write("**Select an action to mitigate this risk:**")
    
    for i, option in enumerate(options, 1):
        if st.button(f"Option {i}: {option}", key=f"opt_{i}", use_container_width=True):
            st.session_state.selected_option = option
            st.session_state.show_summary = True
    
    # Summary Modal
    if st.session_state.get('show_summary', False):
        show_action_summary(risk, st.session_state.selected_option)
    
    if st.button("Cancel", key="cancel_escalation"):
        st.session_state.show_escalation = False
        st.session_state.escalation_options = None
        st.session_state.show_summary = False
        st.rerun()

def show_action_summary(risk, chosen_action):
    """Show summary after action selection."""
    st.markdown("---")
    st.success("### ✅ Escalation Summary")
    
    st.write(f"**Risk Name:** {risk['risk_type'].replace('_', ' ').title()}")
    st.write(f"**Action Taken:** {chosen_action}")
    st.write(f"**Updated Status:** Mitigated")
    st.write(f"**Timestamp:** {datetime.utcnow().isoformat()}")
    
    if st.button("Confirm & Save", type="primary", key="confirm_save"):
        risk['action'] = 'escalate'
        risk['status'] = 'mitigated'  # Changed from 'actioned' to 'mitigated'
        risk['action_taken'] = chosen_action
        risk['reviewed_at'] = datetime.utcnow().isoformat()
        save_risk_action(risk)
        
        st.balloons()
        st.success("Risk escalation recorded successfully!")
        
        # Reset states and reload
        st.session_state.show_escalation = False
        st.session_state.escalation_options = None
        st.session_state.show_summary = False
        st.session_state.selected_risk = None
        st.rerun()

def save_risk_action(risk):
    """Save human decision to risks.json."""
    try:
        # Read fresh data (don't use cache)
        with open("../output/risks.json", "r", encoding="utf-8") as f:
            risks = json.load(f)
        
        # Update the matching risk
        for i, r in enumerate(risks):
            if r['post_id'] == risk['post_id']:
                risks[i] = risk
                break
        
        # Write back to file
        with open("../output/risks.json", "w", encoding="utf-8") as f:
            json.dump(risks, f, indent=2)
        
        # Clear cache so next load gets fresh data
        load_risks.clear()
        st.success("✅ Risk saved successfully!")
    except Exception as e:
        st.error(f"❌ Error saving risk: {e}")

def show_department_view(department, risks_list):
    """Department-level aggregated view."""
    dept_risks = [r for r in risks_list if r['department'] == department]
    
    st.header(f"{department}")
    st.write(f"**{len(dept_risks)} signals** detected")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, key=f"conf_{department}")
    with col2:
        selected_severity = st.multiselect("Risk Level", ["low", "medium", "high", "critical"], 
                                          default=["low", "medium", "high", "critical"],
                                          key=f"sev_{department}")
    with col3:
        days_back = st.number_input("Days", 1, 365, 7, key=f"days_{department}")
    
    # Filter risks
    cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
    filtered = [r for r in dept_risks 
                if r['confidence'] >= min_confidence 
                and r['risk_level'] in selected_severity
                and r['time-detected'] >= cutoff_date]
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Signal Distribution by Type**")
        if filtered:
            type_counts = pd.Series([r['risk_type'] for r in filtered]).value_counts()
            st.bar_chart(type_counts)
        else:
            st.info("No data to display")
    
    with col2:
        st.write("**Confidence Score Distribution**")
        if filtered:
            conf_data = pd.Series([r['confidence'] for r in filtered])
            st.bar_chart(conf_data.value_counts().sort_index())
        else:
            st.info("No data to display")
    
    # Risk Cards
    st.subheader("Risk Cards")
    for risk in filtered:
        with st.expander(f"🔴 {risk['risk_type'].upper()} | Level: {risk['risk_level']} | Conf: {risk['confidence']:.0%}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Summary:** {risk['summary']}")
                st.write(f"**Detected:** {risk['time-detected']}")
            with col2:
                st.write(f"**Status:** {risk.get('status', 'pending')}")
                st.write(f"**Why It Matters:** {risk['why_it_matters']}")
            
            if st.button("View Details", key=f"details_{risk['post_id']}"):
                st.session_state.selected_risk = risk
                st.rerun()

def main():
    st.title("🏦 Mashreq Social Signal Intelligence Dashboard")
    st.write("Governance-Focused Risk Review | No Automated Actions")
    
    risks = load_risks()
    
    if not risks:
        st.warning("No risks loaded. Run agent.py first.")
        return
    
    # Check for selected risk in session
    if 'selected_risk' in st.session_state and st.session_state.selected_risk:
        show_risk_detail(st.session_state.selected_risk, risks)
        return
    
    # Admin Dashboard
    st.subheader("Admin Dashboard")
    
    departments = {
        "Technology & Operations",
        "Customer Support",
        "Marketing & Communications",
        "Risk & Compliance"
    }
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Signals", len(risks))
    with col2:
        high_risk = len([r for r in risks if r['risk_level'] in ['high', 'critical']])
        st.metric("High/Critical", high_risk)
    with col3:
        avg_conf = sum(r['confidence'] for r in risks) / len(risks) if risks else 0
        st.metric("Avg Confidence", f"{avg_conf:.0%}")
    with col4:
        monitored = len([r for r in risks if r.get('status') in ['monitoring', 'validation_requested']])
        st.metric("Under Review", monitored)
    
    st.divider()
    
    # Department Tabs
    tabs = st.tabs(list(departments))
    for tab, dept in zip(tabs, departments):
        with tab:
            show_department_view(dept, risks)

if __name__ == "__main__":
    main()