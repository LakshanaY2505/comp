import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import requests
from agent import OLLAMA_URL, MODEL

st.set_page_config(page_title="Mashreq Social Signal Dashboard", layout="wide")

# Load risks data
@st.cache_data
def load_risks():
    try:
        with open("../output/risks.json", "r") as f:
            return json.load(f)
    except:
        return []

# Load synthetic data for context
@st.cache_data
def load_synthetic_data():
    try:
        with open("../data/synthetic_data.json", "r") as f:
            return json.load(f)
    except:
        return []

def decision_support_chat(risk):
    """AI-powered decision support assistant."""
    st.subheader("Decision Support Assistant")
    st.info("This assistant helps you think through uncertainty. It does not initiate actions.")
    
    user_question = st.text_area("What would you like to explore?", key=f"chat_{risk['post_id']}")
    
    if st.button("Ask Assistant", key=f"btn_{risk['post_id']}"):
        if user_question.strip():
            prompt = f"""
You are a bank risk decision-support assistant. Help the human think through this risk.
Ask clarifying questions and suggest review angles. Do NOT initiate any actions.

Risk Type: {risk['risk_type']}
Risk Level: {risk['risk_level']}
Confidence: {risk['confidence']}
Summary: {risk['summary']}
Why It Matters: {risk['why_it_matters']}

Human Question: {user_question}

Respond with:
1. A clarifying question or two
2. Suggested validation angles
3. Key uncertainties to resolve
"""
            payload = {"model": MODEL, "prompt": prompt, "stream": False}
            try:
                response = requests.post(OLLAMA_URL, json=payload)
                response.raise_for_status()
                assistant_response = response.json()["response"].strip()
                st.write(assistant_response)
            except Exception as e:
                st.error(f"Error: {e}")

def show_risk_detail(risk, risks_list):
    """Detailed risk view with human-in-the-loop workflow."""
    st.header(f"Risk: {risk['risk_type'].upper()}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Risk Level", risk['risk_level'].capitalize())
    with col2:
        st.metric("Confidence", f"{risk['confidence']:.0%}")
    with col3:
        st.metric("Department", risk['department'])
    with col4:
        st.metric("Status", risk.get('status', 'pending').capitalize())
    
    # Explainability Panel
    st.subheader("Explainability Panel")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Why It Matters**")
        st.write(risk['why_it_matters'])
    with col2:
        st.write("**Detection Patterns**")
        st.write(f"- Risk Type: {risk['risk_type']}")
        st.write(f"- Detected: {risk['time-detected']}")
    
    st.write("**What AI is Uncertain About**")
    st.write(f"- Confidence Score: {risk['confidence']} (0.7+ = strong signal)")
    st.write("- No assumption of factual correctness")
    st.write("- Requires human validation")
    
    # Credibility & Scenario Comparison
    st.subheader("Credibility & Context")
    st.write(f"**Risk Summary:** {risk['summary']}")
    st.write(f"**Original Caption:** _{risk['caption']}_")
    
    # Find similar historical signals (mock)
    similar_count = sum(1 for r in risks_list if r.get('risk_type') == risk['risk_type'])
    st.write(f"**Similar Signals:** {similar_count} other {risk['risk_type']} signals in history")
    
    # Human Review Workflow
    st.subheader("Human Review Workflow")
    st.write("**Non-Action Boundaries:**")
    st.write("- ❌ No public response will be generated")
    st.write("- ❌ No assumption of factual correctness")
    st.write("- ❌ No automated escalation")
    st.write("- ✅ All decisions logged for auditability")
    
    st.write("**Suggested Review Paths:**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Monitor for Escalation", key=f"monitor_{risk['post_id']}"):
            risk['action'] = 'monitor'
            risk['status'] = 'monitoring'
            risk['reviewed_at'] = datetime.utcnow().isoformat()
            st.success("✅ Risk marked for monitoring")
            save_risk_action(risk)
    
    with col2:
        if st.button("🔍 Request Internal Validation", key=f"validate_{risk['post_id']}"):
            risk['action'] = 'validate'
            risk['status'] = 'validation_requested'
            risk['reviewed_at'] = datetime.utcnow().isoformat()
            st.success("✅ Validation requested")
            save_risk_action(risk)
    
    with col3:
        if st.button("🤝 Flag for Cross-Team Awareness", key=f"flag_{risk['post_id']}"):
            risk['action'] = 'flag'
            risk['status'] = 'flagged'
            risk['reviewed_at'] = datetime.utcnow().isoformat()
            st.success("✅ Risk flagged for awareness")
            save_risk_action(risk)
    
    with col4:
        if st.button("🗑️ Dismiss as Noise", key=f"dismiss_{risk['post_id']}"):
            risk['action'] = 'dismiss'
            risk['status'] = 'dismissed'
            risk['reviewed_at'] = datetime.utcnow().isoformat()
            st.success("✅ Risk dismissed")
            save_risk_action(risk)
    
    st.divider()
    
    # Decision Support Assistant (Other)
    if st.checkbox("Need more support? Open Decision Assistant", key=f"chat_check_{risk['post_id']}"):
        decision_support_chat(risk)

def save_risk_action(risk):
    """Save human decision to risks.json."""
    risks = load_risks()
    for i, r in enumerate(risks):
        if r['post_id'] == risk['post_id']:
            risks[i] = risk
            break
    with open("../output/risks.json", "w") as f:
        json.dump(risks, f, indent=2)

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
        type_counts = pd.Series([r['risk_type'] for r in filtered]).value_counts()
        st.bar_chart(type_counts)
    
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

def main():
    st.title("🏦 Mashreq Social Signal Intelligence Dashboard")
    st.write("Governance-Focused Risk Review | No Automated Actions")
    
    risks = load_risks()
    
    if not risks:
        st.warning("No risks loaded. Run agent.py first.")
        return
    
    # Check for selected risk in session
    if 'selected_risk' in st.session_state and st.session_state.selected_risk:
        if st.button("← Back to Dashboard"):
            st.session_state.selected_risk = None
            st.rerun()
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
        avg_conf = sum(r['confidence'] for r in risks) / len(risks)
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