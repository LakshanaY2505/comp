import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import os
import time
import plotly.express as px

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here").strip()
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

st.set_page_config(page_title="Mashreq Social Signal Dashboard", layout="wide")

# Load risks data WITHOUT caching so it updates in real-time
def load_risks():
    """Load risks with NO caching to get real-time updates."""
    try:
        with open("../output/risks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure numeric fields are floats
            for risk in data:
                if isinstance(risk.get('confidence'), str):
                    risk['confidence'] = float(risk['confidence'])
                if isinstance(risk.get('credibility_score'), str):
                    risk['credibility_score'] = float(risk['credibility_score'])
            return data
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Error loading risks: {e}")
        return []

def load_history():
    """Load risk history from history.json."""
    try:
        with open("../output/history.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                if isinstance(item.get('confidence'), str):
                    item['confidence'] = float(item['confidence'])
                if isinstance(item.get('credibility_score'), str):
                    item['credibility_score'] = float(item['credibility_score'])
            return data
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Error loading history: {e}")
        return []

def save_to_history(risk):
    """Save a risk to the history log."""
    try:
        history = load_history()
        history.append(risk)
        with open("../output/history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        st.error(f"Error saving to history: {e}")

def generate_escalation_options(summary: str, risk_type: str, risk_level: str):
    """Generate AI-powered escalation options."""
    default_options = ["Monitor virality", "Prepare statement", "Contact affected parties"]
    
    prompt = f"""You are a bank risk response assistant.
Given the risk summary, generate EXACTLY 3 concise action options to address it.
Return ONLY valid JSON in this format:
{{
  "options": ["option 1", "option 2", "option 3"]
}}

Risk Type: {risk_type}
Risk Level: {risk_level}
Summary: {summary}"""
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(OPENAI_URL, json=payload, headers=headers)
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"].strip()
        # Simple JSON extraction
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end != 0:
            data = json.loads(raw_text[start:end])
            options = data.get("options")
            if options and isinstance(options, list) and len(options) > 0:
                return [str(o).strip() for o in options][:3]
    except Exception as e:
        pass
    return default_options

def get_risk_color(risk_level):
    """Get color code for risk level."""
    color_map = {
        'low': '#28a745',      # Green
        'medium': '#ffc107',   # Yellow
        'high': '#fd7e14',     # Orange
        'critical': '#dc3545'  # Red
    }
    return color_map.get(risk_level, '#6c757d')

def get_risk_container(risk_level):
    """Get the appropriate Streamlit container for risk level."""
    if risk_level in ['high', 'critical']:
        return 'error'  # Red
    elif risk_level == 'medium':
        return 'warning'  # Yellow
    else:
        return 'success'  # Green

def show_confidence_meter(confidence, credibility_score=None, is_verified=None, verification_notes=""):
    """Display visual confidence and credibility meters."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Confidence Level**")
        
        # Confidence color coding
        if confidence >= 0.7:
            color = "🟢"
            label = "High Confidence"
        elif confidence >= 0.4:
            color = "🟡"
            label = "Medium Confidence"
        else:
            color = "🔴"
            label = "Low Confidence"
        
        st.markdown(f"### {color} {confidence:.0%} - {label}")
        st.progress(confidence)
    
    with col2:
        st.write("**Credibility**")
        
        if credibility_score is not None:
            # Credibility color coding
            if credibility_score >= 0.7:
                cred_color = "✅"
                cred_label = "Verified"
            elif credibility_score >= 0.4:
                cred_color = "⚠️"
                cred_label = "Unverified"
            else:
                cred_color = "🚫"
                cred_label = "Likely False"
            
            st.markdown(f"### {cred_color} {credibility_score:.0%} - {cred_label}")
            st.progress(credibility_score)
        else:
            st.info("N/A")
    
    if verification_notes:
        st.markdown(f"**Verification Notes:** {verification_notes}")

def chat_sidebar(risk):
    """Sidebar chatbot for risk Q&A."""
    st.sidebar.header("Risk Assistant")
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
    user_input = st.sidebar.text_input("Your question:", key=f"chat_input_{risk['post_id']}")
    send = st.sidebar.button("Send", key=f"send_btn_{risk['post_id']}", use_container_width=True)
    
    if send and user_input.strip():
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        prompt = f"""You are a bank risk analyst assistant. Answer user questions about the risk.
Keep answers concise and grounded in the provided context.

Caption: {risk['caption']}
Risk Type: {risk['risk_type']}
Risk Level: {risk['risk_level']}
Confidence: {risk['confidence']}
Department: {risk['department']}
Why It Matters: {risk['why_it_matters']}
Summary: {risk['summary']}

User Question: {user_input}"""
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            with st.spinner("Assistant is thinking..."):
                response = requests.post(OPENAI_URL, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                answer = response.json()["choices"][0]["message"]["content"].strip()
                st.session_state.chat_history.append({'role': 'assistant', 'content': answer})
        except requests.exceptions.Timeout:
            st.session_state.chat_history.append({'role': 'assistant', 'content': "Request timeout. Please try again."})
        except Exception as e:
            st.session_state.chat_history.append({'role': 'assistant', 'content': f"Error: {str(e)}"})
        
        st.rerun()
    
    # Mark as Mitigated button
    st.sidebar.divider()
    if st.sidebar.button("Mark as Mitigated", key=f"mitigate_btn_{risk['post_id']}", use_container_width=True, type="primary"):
        risk['action'] = 'mitigated'
        risk['status'] = 'mitigated'
        risk['reviewed_at'] = datetime.now(timezone.utc).isoformat()
        save_risk_action(risk)
        st.sidebar.success("Risk marked as mitigated!")
        st.session_state.selected_risk = None
        time.sleep(1)
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
    st.title(f"{risk['risk_type'].replace('_', ' ').title()}")
    
    # Color-coded risk level banner
    risk_level = risk['risk_level']
    container_type = get_risk_container(risk_level)
    
    if container_type == 'error':
        st.error(f"🔴 **CRITICAL/HIGH RISK** - This requires immediate escalation and action")
    elif container_type == 'warning':
        st.warning(f"🟡 **MEDIUM RISK** - Monitor and prepare mitigation measures")
    else:
        st.success(f"🟢 **LOW RISK** - Routine monitoring recommended")
    
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
        st.subheader("Risk Description")
        st.write(risk['summary'])
        
        st.subheader("Why It Matters")
        st.write(risk['why_it_matters'])
        
        st.subheader("Original Caption")
        st.info(risk['caption'])
        
        st.write(f"**Department:** {risk['department']}")
        st.write(f"**Detected:** {risk['time-detected']}")
    
    with col2:
        show_confidence_meter(
            risk['confidence'],
            risk.get('credibility_score', 0.5),
            risk.get('is_verified', False),
            risk.get('verification_notes', '')
        )
        
        st.metric("Risk Level", risk['risk_level'].upper())
    
    st.divider()
    
    # Action Buttons
    st.subheader("⚡ Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Escalate", use_container_width=True, type="primary"):
            st.session_state.show_escalation = True
            st.session_state.escalation_risk = risk
            st.rerun()
    
    with col2:
        if st.button("Dismiss", use_container_width=True):
            risk['action'] = 'dismiss'
            risk['status'] = 'dismissed'
            risk['reviewed_at'] = datetime.now(timezone.utc).isoformat()
            save_risk_action(risk)
            st.success("Risk dismissed")
            st.session_state.selected_risk = None
            st.rerun()
    
    with col3:
        if st.button("Other (Chat)", use_container_width=True):
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
    st.subheader("Escalation Options")
    
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
    
    # Ensure options is not None
    if options is None:
        options = ["Monitor virality", "Prepare statement", "Contact affected parties"]
        st.session_state.escalation_options = options
    
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
    st.success("### Escalation Summary")
    
    st.write(f"**Risk Name:** {risk['risk_type'].replace('_', ' ').title()}")
    st.write(f"**Action Taken:** {chosen_action}")
    st.write(f"**Updated Status:** Mitigated")
    st.write(f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}")
    
    if st.button("Confirm & Save", type="primary", key="confirm_save"):
        risk['action'] = 'escalate'
        risk['status'] = 'mitigated'  # Changed from 'actioned' to 'mitigated'
        risk['action_taken'] = chosen_action
        risk['reviewed_at'] = datetime.now(timezone.utc).isoformat()
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
    """Save human decision to risks.json and history.json."""
    try:
        # Read fresh data (no caching)
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
        
        # Save to history
        save_to_history(risk)
        
        st.success("Risk saved successfully!")
    except Exception as e:
        st.error(f"Error saving risk: {e}")

def show_department_view(department, risks_list):
    """Department-level aggregated view."""
    dept_risks = [r for r in risks_list if r['department'] == department]
    
    st.header(f"{department}")
    st.write(f"**{len(dept_risks)} signals** detected")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, key=f"conf_{department}")
    with col2:
        selected_severity = st.multiselect("Risk Level", ["low", "medium", "high"], 
                                          default=["low", "medium", "high"],
                                          key=f"sev_{department}")
    
    # Filter risks
    filtered = [r for r in dept_risks 
                if r['confidence'] >= min_confidence 
                and r['risk_level'] in selected_severity]
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Risk Distribution by Level**")
        if filtered:
            # Count risks by level
            level_counts = pd.Series([r['risk_level'] for r in filtered]).value_counts()
            
            # Define colors for risk levels
            level_colors = {
                'critical': '#dc3545',
                'high': '#fd7e14',
                'medium': '#ffc107',
                'low': '#28a745'
            }
            color_list = [level_colors.get(level, '#6c757d') for level in level_counts.index]
            
            fig = px.pie(
                values=level_counts.values,
                names=level_counts.index,
                title=f"Risk Levels in {department}",
                color_discrete_sequence=color_list
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display")
    
    with col2:
        st.write("**Risk Distribution by Type**")
        if filtered:
            # Count risks by type
            type_counts = pd.Series([r['risk_type'] for r in filtered]).value_counts()
            # Format the type names for display
            formatted_names = [name.replace('_', ' ').title() for name in type_counts.index]
            
            fig = px.pie(
                values=type_counts.values,
                names=formatted_names,
                title=f"Risk Types in {department}"
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display")
    
    # Risk Cards
    st.subheader("Risk Cards")
    for risk in filtered:
        # Verification status icon
        verified_icon = "✅" if risk.get('is_verified') else "⚠️"
        cred_score = risk.get('credibility_score', 0.5)
        risk_level = risk['risk_level']
        
        # Color-coded container based on risk level
        card_header = f"{verified_icon} {risk['risk_type'].upper()} | Level: {risk_level.upper()} | Conf: {risk['confidence']:.0%} | Cred: {cred_score:.0%}"
        
        with st.expander(card_header):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Summary:** {risk['summary']}")
                st.write(f"**Detected:** {risk['time-detected']}")
                st.write(f"**Verification:** {verified_icon} {'Verified' if risk.get('is_verified') else 'Unverified'}")
            with col2:
                st.write(f"**Status:** {risk.get('status', 'pending')}")
                st.write(f"**Why It Matters:** {risk['why_it_matters']}")
                if risk.get('verification_notes'):
                    st.write(f"**Notes:** {risk['verification_notes']}")
            
            # Color-coded display based on risk level
            container_type = get_risk_container(risk_level)
            if container_type == 'error':
                st.error(f"**HIGH SEVERITY RISK** - Requires immediate attention")
            elif container_type == 'warning':
                st.warning(f"**MEDIUM SEVERITY RISK** - Requires monitoring")
            else:
                st.success(f"✓ **LOW SEVERITY RISK** - Routine monitoring")
            
            if st.button("View Details", key=f"details_{risk['post_id']}"):
                st.session_state.selected_risk = risk
                st.rerun()

def initialize_session_state():
    """Initialize session state for real-time monitoring."""
    if 'last_risk_count' not in st.session_state:
        st.session_state.last_risk_count = 0
    if 'notification_queue' not in st.session_state:
        st.session_state.notification_queue = []
    if 'processed_ids' not in st.session_state:
        st.session_state.processed_ids = set()

def show_notification_popup(risk):
    """Show a notification popup for new risks."""
    dept_icon = {
        "Technology & Operations": "💻",
        "Customer Support": "📞",
        "Marketing & Communications": "📢",
        "Risk & Compliance": "⚖️"
    }
    
    icon = dept_icon.get(risk.get('department'), "🚨")
    
    # Create a visual notification card
    notification_col = st.columns([1, 4])
    with notification_col[0]:
        st.markdown(f"# {icon}")
    
    with notification_col[1]:
        severity_color = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        severity = severity_color.get(risk.get('risk_level', 'low'), '⚪')
        
        st.markdown(f"""
        ### {severity} New Risk Signal Detected
        **Department:** {risk.get('department', 'N/A')}  
        **Type:** {risk.get('risk_type', 'unknown').replace('_', ' ').title()}  
        **Level:** {risk.get('risk_level', 'unknown').upper()}  
        **Confidence:** {risk.get('confidence', 0):.0%}  
        **Caption:** *{risk.get('caption', '')[:80]}...*
        """)

def check_for_new_risks():
    """Check if new risks have arrived and show notifications."""
    risks = load_risks()
    current_count = len(risks)
    
    # Get newly added risks
    if current_count > st.session_state.last_risk_count:
        new_risks = risks[st.session_state.last_risk_count:]
        st.session_state.last_risk_count = current_count
        
        return new_risks
    
    return []

def show_history_view(history_list):
    """Display risk history with details and filters."""
    if not history_list:
        st.info("No history yet. Risks will appear here after you take action on them.")
        return
    
    st.subheader(f"History Log ({len(history_list)} items)")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.multiselect("Status", ["dismissed", "mitigated"], 
                                       default=["dismissed", "mitigated"],
                                       key="hist_status")
    
    with col2:
        type_filter = st.multiselect("Risk Type", 
                                     ["fraud_signal", "service_signal", "rumor", "misinformation", "other"],
                                     default=["fraud_signal", "service_signal", "rumor", "misinformation", "other"],
                                     key="hist_type")
    
    with col3:
        dept_filter = st.multiselect("Department",
                                     list(set(h.get('department', 'Unknown') for h in history_list)),
                                     default=list(set(h.get('department', 'Unknown') for h in history_list)),
                                     key="hist_dept")
    
    # Filter history
    filtered_history = [h for h in history_list 
                       if h.get('status') in status_filter
                       and h.get('risk_type') in type_filter
                       and h.get('department') in dept_filter]
    
    if not filtered_history:
        st.info("No history items match the selected filters.")
        return
    
    # Display as table
    history_data = []
    for h in sorted(filtered_history, key=lambda x: x.get('reviewed_at', x.get('time_detected', '')), reverse=True):
        history_data.append({
            "Post ID": h.get('post_id', 'N/A'),
            "Caption": h.get('caption', '')[:50] + "...",
            "Status": h.get('status', 'N/A').upper(),
            "Type": h.get('risk_type', 'N/A').replace('_', ' ').title(),
            "Level": h.get('risk_level', 'N/A').upper(),
            "Department": h.get('department', 'N/A'),
            "Action Taken": h.get('action', 'N/A').title(),
            "Reviewed At": h.get('reviewed_at', 'N/A')[:10]
        })
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Option to clear history
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Clear History", key="clear_history"):
            try:
                with open("../output/history.json", "w", encoding="utf-8") as f:
                    json.dump([], f)
                st.success("History cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing history: {e}")

def main():
    # Initialize session state
    initialize_session_state()
    
    st.title("Mashreq Social Signal Intelligence Dashboard")
    st.write("Real-Time Risk Monitoring | User-Driven Decision Making")
    
    # Auto-refresh every 2 seconds
    st.markdown("""
    <script>
    setTimeout(function() {
        window.location.reload();
    }, 2000);
    </script>
    """, unsafe_allow_html=True)
    
    risks = load_risks()
    
    if not risks:
        st.info("Waiting for risk signals... The dashboard will auto-refresh as risks arrive.")
        return
    
    # Check for new risks and show notifications
    new_risks = check_for_new_risks()
    
    if new_risks:
        st.markdown("---")
        st.subheader("Urgent Risk Alerts")
        
        # Filter for high and critical risks only
        high_risks = [r for r in new_risks if r['risk_level'] in ['high', 'critical']]
        
        for risk in high_risks:
            if risk['post_id'] not in st.session_state.processed_ids:
                with st.container(border=True):
                    show_notification_popup(risk)
                    st.session_state.processed_ids.add(risk['post_id'])
        
        st.markdown("---")
    
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
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Signals", len(risks))
    with col2:
        high_risk = len([r for r in risks if r['risk_level'] in ['high', 'critical']])
        st.metric("Critical/High", high_risk)
    with col3:
        medium_risk = len([r for r in risks if r['risk_level'] == 'medium'])
        st.metric("Medium", medium_risk)
    with col4:
        avg_conf = sum(r['confidence'] for r in risks) / len(risks) if risks else 0
        st.metric("Avg Confidence", f"{avg_conf:.0%}")
    with col5:
        actioned = len([r for r in risks if r.get('status') in ['mitigated', 'actioned']])
        st.metric("Actioned", actioned)
    
    st.divider()
    
    # Department Tabs + History Tab
    tab_names = list(departments) + ["History"]
    tabs = st.tabs(tab_names)
    
    for tab, dept in zip(tabs[:-1], departments):
        with tab:
            show_department_view(dept, risks)
    
    # History Tab
    with tabs[-1]:
        history = load_history()
        show_history_view(history)

if __name__ == "__main__":
    main()