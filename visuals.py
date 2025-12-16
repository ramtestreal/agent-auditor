import streamlit as st
import plotly.graph_objects as go

def calculate_score(audit_data):
    """Calculates a score out of 100 based on findings"""
    score = 0
    total_checks = 5
    
    # 1. Robots.txt
    if audit_data['gates']['robots.txt'] == "Found":
        score += 20
        
    # 2. AI Access (Critical)
    if "Allowed" in audit_data['gates']['ai_access']:
        score += 20
        
    # 3. Sitemap
    if "Found" in audit_data['gates']['sitemap.xml']:
        score += 20
        
    # 4. Schema
    if audit_data['schema_count'] > 0:
        score += 20
        
    # 5. AI.txt OR Manifest (Bonus points)
    if "Found" in audit_data['gates']['ai.txt'] or "Found" in audit_data['manifest']:
        score += 20
        
    return score

def create_gauge_chart(score):
    """Creates the rounded gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Agentic Readiness Score"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "black"},
            'steps': [
                {'range': [0, 50], 'color': "#ff4b4b"},  # Red
                {'range': [50, 80], 'color': "#ffa421"}, # Orange
                {'range': [80, 100], 'color': "#0df05e"} # Green
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def display_dashboard(audit_data):
    """Main function to display the graphics"""
    
    # 1. Calculate Score
    score = calculate_score(audit_data)
    
    # 2. Display Top Section (Gauge + Stack)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.plotly_chart(create_gauge_chart(score), use_container_width=True)
        
    with col2:
        st.markdown("### 🏗️ Tech Stack Detected")
        st.info(f"{audit_data['stack']}")
        if score < 50:
            st.error("❌ High Risk: Agents will ignore this site.")
        elif score < 80:
            st.warning("⚠️ Partial Access: Agents might struggle.")
        else:
            st.success("✅ Certified: Agentic Ready!")

    st.divider()

    # 3. Status Grid (The "Vertical Cards")
    st.markdown("### 🛡️ Security & Access Gates")
    
    # Define status colors/icons
    def get_status_visual(status, label):
        if "Found" in status or "Allowed" in status:
            return "✅", "PASS", status
        elif "Missing" in status:
            return "❌", "FAIL", "Missing"
        else:
            return "⚠️", "WARN", status

    # Create 4 columns for metrics
    m1, m2, m3, m4 = st.columns(4)
    
    # Robots.txt
    icon, state, desc = get_status_visual(audit_data['gates']['robots.txt'], "Robots.txt")
    m1.metric(label="1. Robots.txt", value=state, delta=icon)
    
    # AI Access
    icon, state, desc = get_status_visual(audit_data['gates']['ai_access'], "AI Access")
    m2.metric(label="2. AI Blocking", value=state, delta=icon)
    
    # AI.txt
    icon, state, desc = get_status_visual(audit_data['gates']['ai.txt'], "ai.txt")
    m3.metric(label="3. ai.txt File", value=state, delta=icon)
    
    # Sitemap
    icon, state, desc = get_status_visual(audit_data['gates']['sitemap.xml'], "Sitemap")
    m4.metric(label="4. Sitemap", value=state, delta=icon)
    
    st.divider()
    
    # 4. Data Layer (Schema & Manifest)
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🧠 Semantic Data (Schema)")
        if audit_data['schema_count'] > 0:
            st.metric(label="Schema Objects", value=audit_data['schema_count'], delta="Active")
            st.progress(100, text="Data is readable")
        else:
            st.metric(label="Schema Objects", value="0", delta="- Critical")
            st.progress(0, text="Data is invisible")
            
    with c2:
        st.markdown("#### 🆔 App Identity (Manifest)")
        if "Found" in audit_data['manifest']:
            st.metric(label="Manifest Status", value="Verified", delta="Active")
            st.progress(100, text="App-like experience")
        else:
            st.metric(label="Manifest Status", value="Missing", delta="- Warning")
            st.progress(0, text="Not installable")

    st.divider()
