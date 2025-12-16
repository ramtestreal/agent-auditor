import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import io
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Agentic Readiness Auditor Pro", page_icon="🕵️‍♂️", layout="wide")

# Sidebar
st.sidebar.title("🕵️‍♂️ Audit Controls")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# --- FUNCTIONS ---

def detect_tech_stack(soup, headers):
    """Detects if the site is WP, Shopify, Next.js, etc."""
    stack = []
    html = str(soup)
    
    # Check Meta Generators & Script signatures
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
        
    # Check Headers
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
        s = requests.get(f"{domain}/sitemap.xml", timeout=3)
        gates['sitemap.xml'] = "Found" if s.status_code == 200 else "Missing"
    except:
        gates['sitemap.xml'] = "Error"

    # 3. ai.txt (The new standard)
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
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    status_text = st.empty()
    status_text.text("Connecting to website...")
    
    try:
        # Fetch Page
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AgenticAuditor/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
        
        # 4. AI Manifest
        manifest_res = requests.get(f"{url.rstrip('/')}/.well-known/ai-plugin.json", timeout=3)
        manifest_status = "Found" if manifest_res.status_code == 200 else "Missing"

        # Compile Data
        audit_data = {
            "url": url,
            "stack": stack,
            "gates": gates,
            "schema_count": len(schemas),
            "schema_sample": schema_sample,
            "manifest": manifest_status
        }
        
        # Generate Recs
        recs = generate_recommendations(audit_data)
        
        # 5. Gemini Analysis
        status_text.text("Generative AI is analyzing the report...")
        prompt = f"""
        Analyze this technical audit for 'Agentic Commerce Readiness'.
        Target URL: {url}
        Tech Stack: {stack}
        Security Gates: {gates}
        Schema Found: {len(schemas)} items.
        Manifest: {manifest_status}
        
        Write a professional Executive Summary (3 sentences) explaining if an AI Agent can buy from this site or not.
        Then, explain the business impact of the missing elements.
        """
        ai_summary = model.generate_content(prompt).text
        
        return audit_data, recs, ai_summary

    except Exception as e:
        st.error(f"Audit Failed: {str(e)}")
        return None, None, None

# --- UI LAYOUT ---
st.title("🤖 Agentic Readiness Auditor Pro")
st.markdown("### The Standard for Future Commerce")
st.info("Check if your client's website is ready for the **Agent Economy** (Mastercard/Visa Agents, ChatGPT, Gemini).")

url_input = st.text_input("Enter Client Website URL", placeholder="https://www.example-hotel.com")

if st.button("🚀 Run Full Audit"):
    if not api_key or not url_input:
        st.error("Please provide both API Key and URL.")
    else:
        audit_data, recs, ai_summary = perform_audit(url_input, api_key)
        
        if audit_data:
            # --- DISPLAY RESULTS ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Technology Stack")
                st.code(audit_data['stack'])
                
                st.subheader("2. Security Gates")
                st.json(audit_data['gates'])

            with col2:
                st.subheader("3. Agentic Data (Schema)")
                st.metric("Schema Objects Found", audit_data['schema_count'])
                st.caption("Manifest Status: " + audit_data['manifest'])
                
            st.divider()
            
            st.subheader("📝 Executive Summary")
            st.write(ai_summary)
            
            st.subheader("🔧 Priority Recommendations")
            for rec in recs:
                st.warning(rec)
                
            # --- EXCEL REPORT GENERATION ---
            # Create a Pandas DataFrame for the report
            report_dict = {
                "Metric": ["Target URL", "Tech Stack", "Robots.txt Status", "AI.txt Status", "Schema Objects", "AI Manifest"],
                "Status": [
                    audit_data['url'],
                    audit_data['stack'],
                    audit_data['gates']['robots.txt'],
                    audit_data['gates']['ai.txt'],
                    f"{audit_data['schema_count']} found",
                    audit_data['manifest']
                ]
            }
            df_report = pd.DataFrame(report_dict)
            
            # Convert to Excel in memory
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_report.to_excel(writer, sheet_name='Audit Summary', index=False)
                # Write Recommendations to a second sheet
                df_recs = pd.DataFrame(recs, columns=["Actionable Recommendations"])
                df_recs.to_excel(writer, sheet_name='Action Plan', index=False)
                
            # Download Button
            st.download_button(
                label="📥 Download Professional Audit Report (Excel)",
                data=buffer,
                file_name=f"Agentic_Audit_{int(time.time())}.xlsx",
                mime="application/vnd.ms-excel"
            )
