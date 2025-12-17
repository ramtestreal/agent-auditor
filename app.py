import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import io
import time
import visuals  # Ensure visuals.py exists in your repo

# --- CONFIGURATION ---
st.set_page_config(page_title="Agentic Readiness Auditor Pro", page_icon="🕵️‍♂️", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if 'audit_data' not in st.session_state:
    st.session_state['audit_data'] = None
if 'recs' not in st.session_state:
    st.session_state['recs'] = None
if 'ai_summary' not in st.session_state:
    st.session_state['ai_summary'] = None
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

# --- FUNCTIONS ---

def detect_tech_stack(soup, headers):
    """Detects if the site is WP, Shopify, Next.js, etc."""
    stack = []
    html = str(soup)
    
    if "wp-content" in html or "WordPress" in str(soup.find("meta", attrs={"name": "generator"})):
        stack.append("WordPress")
    if "cdn.shopify.com" in html or "Shopify" in html:
        stack.append("Shopify")
    if "woocommerce" in html:
        stack.append("WooCommerce")
    if "__NEXT_DATA__" in html:
        stack.append("Next.js (React)")
    if "data-reactroot" in html:
        stack.append("React")
    if "Wix" in html or "wix-warmup-data" in html:
        stack.append("Wix")
        
    if "X-Powered-By" in headers:
        stack.append(f"Server: {headers['X-Powered-By']}")
        
    return ", ".join(stack) if stack else "Custom/Unknown Stack"

def check_security_gates(url):
    """Checks robots.txt, sitemap, and ai.txt"""
    domain = url.rstrip('/')
    gates = {}
    
    # 1. Robots.txt
    try:
        r = requests.get(f"{domain}/robots.txt", timeout=3)
        if r.status_code == 200:
            gates['robots.txt'] = "Found"
            if "GPTBot" in r.text and "Disallow" in r.text:
                gates['ai_access'] = "BLOCKED (Critical Issue)"
            else:
                gates['ai_access'] = "Allowed"
        else:
            gates['robots.txt'] = "Missing"
            gates['ai_access'] = "Uncontrolled (Risky)"
    except:
        gates['robots.txt'] = "Error"
        gates['ai_access'] = "Unknown"

    # 2. Sitemap
    try:
        s1 = requests.get(f"{domain}/sitemap.xml", timeout=3)
        s2 = requests.get(f"{domain}/sitemaps.xml", timeout=3)
        s3 = requests.get(f"{domain}/sitemap_index.xml", timeout=3)
        s4 = requests.get(f"{domain}/wp-sitemap.xml", timeout=3)

        if s1.status_code == 200:
            gates['sitemap.xml'] = "Found (Standard)"
        elif s2.status_code == 200:
            gates['sitemap.xml'] = "Found (sitemaps.xml)"
        elif s3.status_code == 200:
            gates['sitemap.xml'] = "Found (sitemap_index.xml)"
        elif s4.status_code == 200:
            gates['sitemap.xml'] = "Found (wp-sitemap.xml)"
        else:
            gates['sitemap.xml'] = "Missing"
    except:
        gates['sitemap.xml'] = "Error checking"

    # 3. ai.txt
    try:
        a = requests.get(f"{domain}/ai.txt", timeout=3)
        gates['ai.txt'] = "Found (Future Proof!)" if a.status_code == 200 else "Missing"
    except:
        gates['ai.txt'] = "Error"
        
    return gates

def generate_recommendations(audit_data):
    """Generates hard-coded logic recommendations"""
    recs = []
    
    if "BLOCKED" in audit_data['gates']['ai_access']:
        recs.append("CRITICAL: Update robots.txt to whitelist 'GPTBot', 'CCBot', and 'Google-Extended'.")
    if audit_data['schema_count'] == 0:
        recs.append("HIGH PRIORITY: Implement JSON-LD Schema. The Agent cannot see your products/prices.")
    if "Missing" in audit_data['gates']['ai.txt']:
        recs.append("OPTIMIZATION: Create an 'ai.txt' file to explicitly grant permission to specific AI models.")
    if "Next.js" in audit_data['stack'] and audit_data['schema_count'] == 0:
        recs.append("TECH FIX: Your Next.js site might be client-side rendering. Ensure Schema is injected via Server Side Rendering (SSR).")

    return recs

def perform_audit(url, api_key):
    genai.configure(api_key=api_key)
    # FIX: gemini-2.5 does not exist. Corrected to 1.5-flash for stability.
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    status_text = st.empty()
    status_text.text("Connecting to website...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AgenticAuditor/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- EXTRACT SITE CONTEXT ---
        page_title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_desc_text = meta_desc["content"] if meta_desc else "No Description"
        body_text = soup.body.get_text(separator=' ', strip=True)[:2000] if soup.body else ""
        
        site_context = f"Title: {page_title}\nDescription: {meta_desc_text}\nPage Content: {body_text}"
        
        # 1. Tech Stack
        status_text.text("Detecting Technology Stack...")
        stack = detect_tech_stack(soup, response.headers)
        
        # 2. Security Gates
        status_text.text("Checking Security Gates (robots.txt, ai.txt)...")
        gates = check_security_gates(url)
        
        # 3. Schema Check
        status_text.text("Extracting Semantic Data...")
        schemas = soup.find_all('script', type='application/ld+json')
        schema_sample = schemas[0].string[:500] if schemas else "None"
        
        # 4. Manifest / Identity Check
        status_text.text("Verifying Identity Files...")
        domain = url.rstrip('/')
        
        plugin_res = requests.get(f"{domain}/.well-known/ai-plugin.json", timeout=3)
        web_manifest_res = requests.get(f"{domain}/manifest.json", timeout=3)
        html_manifest = soup.find("link", rel="manifest")
        
        if plugin_res.status_code == 200:
            manifest_status = "Found (AI Plugin)"
        elif web_manifest_res.status_code == 200:
            manifest_status = "Found (Web Manifest)"
        elif html_manifest:
            manifest_status = "Found (Linked in HTML)"
        else:
            manifest_status = "Missing"

        # Compile Data
        audit_data = {
            "url": url,
            "stack": stack,
            "gates": gates,
            "schema_count": len(schemas),
            "schema_sample": schema_sample,
            "manifest": manifest_status
        }
        
        recs = generate_recommendations(audit_data)
        
        # 5. Gemini Analysis
        status_text.text("Generative AI is reading the content to identify business type...")
        prompt = f"""
        You are a Senior Technical Consultant. Analyze this website for 'Agentic Readiness'.
        
        TARGET DATA:
        - URL: {url}
        - Tech Stack: {stack}
        - Security Gates: {gates}
        - Schema Found: {len(schemas)} items.
        - Manifest Status: {manifest_status}
        
        WEBSITE CONTEXT:
        {site_context}
        
        YOUR TASK:
        1. Detect the Business Type (E-commerce, SaaS, B2B, Blog, etc.) based on the context.
        
        2. GENERATE A REPORT IN STRICT MARKDOWN FORMAT:
        
        ### 1. Executive Summary
        - Write exactly 3 short, punchy sentences.
        - Use **Bold** for key terms.
        - Tailor the language to the business type.
            
        ### 2. Business Impact Analysis
        - Provide in Bullet Points with brief of your technical observations.
        - Each bullet must start with a **Bold Issue**.
        - Keep each bullet upto 38 words length.
        
        Do NOT write paragraphs too long. Delivering messages that are easy to understand.
        """
        
        ai_summary = model.generate_content(prompt).text
        
        status_text.empty()
        return audit_data, recs, ai_summary

    except Exception as e:
        st.error(f"Audit Failed: {str(e)}")
        return None, None, None

# --- UI LAYOUT ---
st.title("🤖 Agentic Readiness Auditor Pro")
st.markdown("### The Standard for Future Commerce")
st.info("Check if your client's website is ready for the **Agent Economy** (Mastercard/Visa Agents, ChatGPT, Gemini).")

# Sidebar
st.sidebar.title("🕵️‍♂️ Audit Controls")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# Main Input
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

url_input = st.text_input("Enter Client Website URL", value=st.session_state['current_url'], placeholder="https://www.example-hotel.com")

# --- UI FIX: Create a Container for the Report ---
# This acts as a dedicated screen area we can wipe clean instantly.
report_view = st.empty()

if st.button("🚀 Run Full Audit"):
    if not api_key or not url_input:
        st.error("Please provide both API Key and URL.")
    else:
        # 1. UI FIX: Wipe the old report INSTANTLY
        report_view.empty()
        
        # 2. UI FIX: Clear the data in memory
        st.session_state['audit_data'] = None
        st.session_state['recs'] = None
        st.session_state['ai_summary'] = None
        
        # Save current URL
        st.session_state['current_url'] = url_input
        
        # Run Audit
        data, recommendations, summary = perform_audit(url_input, api_key)
        
        if data:
            st.session_state['audit_data'] = data
            st.session_state['recs'] = recommendations
            st.session_state['ai_summary'] = summary

# --- DISPLAY RESULTS (Inside the Container) ---
# We render everything inside 'report_view' so it is strictly controlled.
if st.session_state['audit_data']:
    with report_view.container():
        st.success("✅ Audit Complete!")
        
        # 1. Graphical Dashboard
        visuals.display_dashboard(st.session_state['audit_data'])

        st.divider()  
        
        # 2. Text Report
        st.subheader("📝 Executive Summary")
        st.write(st.session_state['ai_summary'])
        
        st.subheader("🔧 Priority Recommendations")
        for rec in st.session_state['recs']:
            st.warning(rec)
            
        # 3. Excel Report Generation
        report_dict = {
            "Metric": ["Target URL", "Tech Stack", "Robots.txt Status", "AI.txt Status", "Schema Objects", "AI Manifest"],
            "Status": [
                st.session_state['audit_data']['url'],
                st.session_state['audit_data']['stack'],
                st.session_state['audit_data']['gates']['robots.txt'],
                st.session_state['audit_data']['gates']['ai.txt'],
                f"{st.session_state['audit_data']['schema_count']} found",
                st.session_state['audit_data']['manifest']
            ]
        }
        df_report = pd.DataFrame(report_dict)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_report.to_excel(writer, sheet_name='Audit Summary', index=False)
            df_recs = pd.DataFrame(st.session_state['recs'], columns=["Actionable Recommendations"])
            df_recs.to_excel(writer, sheet_name='Action Plan', index=False)
            
        # 4. Buttons (Download & New Audit)
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 Download Excel Report",
                data=buffer,
                file_name=f"Agentic_Audit_{int(time.time())}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        with col2:
            if st.button("🔄 Start New Audit"):
                # Clear Session State
                st.session_state['audit_data'] = None
                st.session_state['recs'] = None
                st.session_state['ai_summary'] = None
                st.session_state['current_url'] = ""
                st.rerun()
