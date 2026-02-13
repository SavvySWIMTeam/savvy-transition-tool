import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
import textwrap
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Savvy Transition Generator", page_icon="📄")
NAVY = '#1a3751'
GREEN = '#2e7d32'
RED = '#c62828'
INTERNAL_PASSWORD = "SavvyTeam2025"
DEFAULT_LOGO_FILENAME = "savvy_logo.png"

# --- PASSWORD PROTECTION ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("🔒 Internal Team Access")
    pwd = st.text_input("Enter Internal Password", type="password")
    if st.button("Log In"):
        if pwd == INTERNAL_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# --- MAIN APP LOGIC ---
def generate_savvy_pdf(excel_file, client_name, uploaded_logo=None):
    buffer = io.BytesIO()
    try:
        # Load Excel
        xlsx = pd.ExcelFile(excel_file)
        dfs = {}
        required_sheets = {
            'Model Tolerance': 'Model Tolerance',
            'Holding and Trade Details': 'Holding and Trade Details', 
            'Gain Loss Details': 'Gain Loss Details',
            'Account and Cash Details': 'Account and Cash Details'
        }
        
        for key, sheet_name in required_sheets.items():
            found = next((s for s in xlsx.sheet_names if sheet_name in s), None)
            if found:
                dfs[key] = pd.read_excel(xlsx, sheet_name=found)
            else:
                return None, f"Missing sheet: {sheet_name}. Check Orion Export."

        mt_df = dfs['Model Tolerance']
        ht_df = dfs['Holding and Trade Details']
        gl_df = dfs['Gain Loss Details']
        ac_df = dfs['Account and Cash Details']

        # 1. Model Name - Robust Logic (Skip "Unassigned")
        model_guesses = ht_df['Model Category'].dropna().unique()
        valid_models = [str(m).strip() for m in model_guesses if str(m).strip().lower() != 'unassigned']
        target_model = valid_models[0] if valid_models else "Savvy Strategic Model"

        # 2. Asset Allocation - Clean Names & Wrap
        aa = mt_df[['Class', 'Current %', 'Target %', 'Trade $']].copy()
        for prefix in ['Savvy Total Portfolios - ', 'Savvy US Equity - ', 'Savvy Strategic 90/10 ', 'STP - Moderate Aggressive - ']:
            aa['Class'] = aa['Class'].str.replace(prefix, '', regex=False)
        
        # Normalize punctuation to save space
        aa['Class'] = aa['Class'].str.replace('U.S.', 'US', regex=False).str.strip()
        
        aa['Change %'] = aa['Target %'] - aa['Current %']
        aa = aa.sort_values('Target %', ascending=False).reset_index(drop=True)
        
        cash_idx = aa[aa['Class'].str.contains('Cash', case=False)].index
        if not cash_idx.empty: aa.loc[cash_idx[0], 'Class'] = 'Cash Equivalents'

        # 3. Trades - Filter and Process
        trades = ht_df[ht_df['Trade $'].notna() & (ht_df['Trade $'] != 0)].copy()
        # EXCLUDE CUSTODIAL CASH
        trades = trades[~trades['Ticker'].astype(str).str.contains('CUSTODIAL_CASH', case=False, na=False)]
        
        trades['abs_trade'] = trades['Trade $'].abs()
        # Professional account masking
        trades['Acct4'] = trades['Account Number'].astype(str).str.split('.').str[0].str[-4:]
        
        if 'Trade G/L $' not in trades.columns:
            trades['Trade G/L $'] = 0.0
        trades['Trade G/L $'] = trades['Trade G/L $'].fillna(0)

        buys = trades[trades['Trade $'] > 0].sort_values('abs_trade', ascending=False).head(5)
        sells = trades[trades['Trade $'] < 0].sort_values('abs_trade', ascending=False).head(5)

        # 4. Financials
        cg = gl_df.iloc[0]
        total_val = ac_df['Account Value'].sum()

        # 5. Determine Logo
        logo_img = None
        if uploaded_logo is not None:
            try: logo_img = Image.open(uploaded_logo)
            except: pass
        elif os.path.exists(DEFAULT_LOGO_FILENAME):
            try: logo_img = Image.open(DEFAULT_LOGO_FILENAME)
            except: pass

        # 6. Generate PDF
        with PdfPages(buffer) as pdf:
            # --- PAGE 1 ---
            fig = plt.figure(figsize=(8.5, 11), dpi=300)
            # Lifted bottom margin (0.12) to clear the page edge
            gs = gridspec.GridSpec(6, 1, height_ratios=[1.2, 1.0, 0.2, 5.5, 1.8, 0.3], hspace=0.15, left=0.08, right=0.92, top=0.92, bottom=0.12)
            
            # Header
            ax_h = fig.add_subplot(gs[0]); ax_h.axis('off')
            ax_h.text(0, 0.8, "Portfolio Transition Analysis", fontsize=24, fontweight='bold', color=NAVY)
            ax_h.text(0, 0.5, f"CLIENT: {client_name.upper()}", fontsize=10, fontweight='bold', color='#444444')
            ax_h.text(0, 0.3, f"TARGET MODEL: {target_model}", fontsize=10, color='#666666')
            ax_h.axhline(y=0.1, color=NAVY, linewidth=2)
            
            if logo_img:
                ax_logo = fig.add_axes([0.70, 0.87, 0.20, 0.06], anchor='NE', zorder=10)
                ax_logo.axis('off'); ax_logo.imshow(logo_img)
            else:
                ax_h.text(1, 0.8, "Savvy", fontsize=24, fontweight='black', color=NAVY, ha='right')

            # Metrics
            ax_m = fig.add_subplot(gs[1]); ax_m.axis('off')
            ax_m.add_patch(plt.Rectangle((0, 0.1), 1, 0.8, color='#f4f6f8', zorder=0, transform=ax_m.transAxes))
            metrics = [("TOTAL VALUE", f"${total_val:,.2f}"), ("TRANSITION G/L", f"${cg['Trade Total Gain $']:,.2f}"),
                       ("ESTIMATED TAX", f"${cg['Estimated Tax']:,.2f}"), ("TAX IMPACT %", f"{(cg['Estimated Tax']/total_val)*100:.2f}%")]
            for i, (l, v) in enumerate(metrics):
                ax_m.text(0.05 + i*0.25, 0.65, l, fontsize=7, fontweight='bold', color='#888888', transform=ax_m.transAxes)
                ax_m.text(0.05 + i*0.25, 0.35, v, fontsize=12, fontweight='bold', color=NAVY, transform=ax_m.transAxes)

            # AA Table
            ax_a = fig.add_subplot(gs[3]); ax_a.axis('off')
            ax_a.text(0, 1.0, "ASSET ALLOCATION SUMMARY", fontsize=11, fontweight='bold', color=NAVY, transform=ax_a.transAxes)
            
            rows = [[textwrap.fill(r['Class'], 30), f"{r['Current %']:.2f}%", f"{r['Target %']:.2f
