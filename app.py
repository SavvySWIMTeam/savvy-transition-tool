{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import matplotlib.pyplot as plt\
import matplotlib.gridspec as gridspec\
from matplotlib.backends.backend_pdf import PdfPages\
import textwrap\
import io\
\
# --- CONFIGURATION ---\
st.set_page_config(page_title="Savvy Transition Generator", page_icon="\uc0\u55357 \u56516 ")\
NAVY = '#1a3751'\
GREEN = '#2e7d32'\
RED = '#c62828'\
INTERNAL_PASSWORD = "SavvyTeam2025"  # <--- Share this password with your team\
\
# --- PASSWORD PROTECTION ---\
def check_password():\
    """Returns `True` if the user had the correct password."""\
    if "password_correct" not in st.session_state:\
        st.session_state["password_correct"] = False\
\
    if st.session_state["password_correct"]:\
        return True\
\
    st.title("\uc0\u55357 \u56594  Internal Team Access")\
    pwd = st.text_input("Enter Internal Password", type="password")\
\
    if st.button("Log In"):\
        if pwd == INTERNAL_PASSWORD:\
            st.session_state["password_correct"] = True\
            st.rerun()\
        else:\
            st.error("Incorrect password.")\
    return False\
\
if not check_password():\
    st.stop()\
\
# --- MAIN APP LOGIC ---\
def generate_savvy_pdf(excel_file, client_name):\
    buffer = io.BytesIO()\
    try:\
        xlsx = pd.ExcelFile(excel_file)\
        dfs = \{\}\
        required_sheets = \{\
            'Model Tolerance': 'Model Tolerance',\
            'Holding and Trade Details': 'Holding and Trade Details', \
            'Gain Loss Details': 'Gain Loss Details',\
            'Account and Cash Details': 'Account and Cash Details'\
        \}\
\
        for key, sheet_name in required_sheets.items():\
            found = next((s for s in xlsx.sheet_names if sheet_name in s), None)\
            if found:\
                dfs[key] = pd.read_excel(xlsx, sheet_name=found)\
            else:\
                return None, f"Missing sheet: \{sheet_name\}. Check Orion Export."\
\
        mt_df = dfs['Model Tolerance']\
        ht_df = dfs['Holding and Trade Details']\
        gl_df = dfs['Gain Loss Details']\
        ac_df = dfs['Account and Cash Details']\
\
        model_guesses = ht_df['Model Category'].dropna().unique()\
        target_model = model_guesses[0] if len(model_guesses) > 0 else "Savvy Strategic Model"\
\
        aa = mt_df[['Class', 'Current %', 'Target %', 'Trade $']].copy()\
        for prefix in ['Savvy Total Portfolios - ', 'Savvy US Equity - ', 'Savvy Strategic 90/10 ', 'STP - Moderate Aggressive - ']:\
            aa['Class'] = aa['Class'].str.replace(prefix, '', regex=False)\
        aa['Change %'] = aa['Target %'] - aa['Current %']\
        aa = aa.sort_values('Target %', ascending=False).reset_index(drop=True)\
\
        cash_idx = aa[aa['Class'].str.contains('Cash', case=False)].index\
        if not cash_idx.empty: aa.loc[cash_idx[0], 'Class'] = 'Cash Equivalents'\
\
        trades = ht_df[ht_df['Trade $'].notna() & (ht_df['Trade $'] != 0)].copy()\
        trades['abs_trade'] = trades['Trade $'].abs()\
        trades['Acct4'] = trades['Account Number'].astype(str).str[-4:]\
        buys = trades[trades['Trade $'] > 0].sort_values('abs_trade', ascending=False).head(5)\
        sells = trades[trades['Trade $'] < 0].sort_values('abs_trade', ascending=False).head(5)\
\
        cg = gl_df.iloc[0]\
        total_val = ac_df['Account Value'].sum()\
\
        with PdfPages(buffer) as pdf:\
            fig = plt.figure(figsize=(8.5, 11), dpi=300)\
            gs = gridspec.GridSpec(6, 1, height_ratios=[1.2, 1.0, 0.2, 5.5, 1.8, 0.3], hspace=0.15, left=0.08, right=0.92, top=0.92, bottom=0.08)\
\
            ax_h = fig.add_subplot(gs[0]); ax_h.axis('off')\
            ax_h.text(0, 0.8, "Portfolio Transition Analysis", fontsize=24, fontweight='bold', color=NAVY)\
            ax_h.text(1, 0.8, "Savvy", fontsize=24, fontweight='black', color=NAVY, ha='right')\
            ax_h.text(0, 0.5, f"CLIENT: \{client_name.upper()\}", fontsize=10, fontweight='bold', color='#444444')\
            ax_h.text(0, 0.3, f"TARGET MODEL: \{target_model\}", fontsize=10, color='#666666')\
            ax_h.axhline(y=0.1, color=NAVY, linewidth=2)\
\
            ax_m = fig.add_subplot(gs[1]); ax_m.axis('off')\
            ax_m.add_patch(plt.Rectangle((0, 0.1), 1, 0.8, color='#f4f6f8', zorder=0, transform=ax_m.transAxes))\
            metrics = [("TOTAL VALUE", f"$\{total_val:,.2f\}"), ("TRANSITION G/L", f"$\{cg['Trade Total Gain $']:,.2f\}"),\
                       ("ESTIMATED TAX", f"$\{cg['Estimated Tax']:,.2f\}"), ("TAX IMPACT %", f"\{(cg['Estimated Tax']/total_val)*100:.2f\}%")]\
            for i, (l, v) in enumerate(metrics):\
                ax_m.text(0.05 + i*0.25, 0.65, l, fontsize=7, fontweight='bold', color='#888888', transform=ax_m.transAxes)\
                ax_m.text(0.05 + i*0.25, 0.35, v, fontsize=12, fontweight='bold', color=NAVY, transform=ax_m.transAxes)\
\
            ax_a = fig.add_subplot(gs[3]); ax_a.axis('off')\
            ax_a.text(0, 1.0, "ASSET ALLOCATION SUMMARY", fontsize=11, fontweight='bold', color=NAVY, transform=ax_a.transAxes)\
            rows = [[textwrap.fill(r['Class'], 35), f"\{r['Current %']:.2f\}%", f"\{r['Target %']:.2f\}%", f"\{r['Change %']:+.2f\}%", f"$\{r['Trade $']:,.2f\}"] for _, r in aa.iterrows()]\
            table = ax_a.table(cellText=rows, colLabels=['Asset Class', 'Current %', 'Target %', 'Change %', 'Trade Amount'], loc='upper center', cellLoc='left', bbox=[0, 0, 1, 0.95])\
            table.auto_set_font_size(False); table.set_fontsize(9)\
            for (r, c), cell in table.get_celld().items():\
                cell.set_edgecolor('#e0e0e0'); cell.set_linewidth(0.5)\
                if r == 0: cell.set_facecolor(NAVY); cell.set_text_props(color='white', weight='bold', ha='center')\
                else:\
                    if c in [1,2,3]: cell.get_text().set_ha('center')\
                    if c==4: cell.get_text().set_ha('right')\
                    if c in [3,4]:\
                        val = float(str(rows[r-1][c]).replace('%','').replace('$','').replace(',',''))\
                        if val != 0: cell.get_text().set_color(GREEN if val > 0 else RED); cell.get_text().set_weight('bold')\
\
            ax_t = fig.add_subplot(gs[4]); ax_t.axis('off')\
            ax_t.text(0, 1.0, "TAX & REALIZED GAIN DETAILS", fontsize=11, fontweight='bold', color=NAVY, transform=ax_t.transAxes)\
            t_rows = [["Short-Term Gains", f"$\{cg['Trade Short Term Gain']:,.2f\}"], ["Long-Term Gains", f"$\{cg['Trade Long Term Gain']:,.2f\}"],\
                      ["Total Realized Gain", f"$\{cg['Trade Total Gain $']:,.2f\}"], ["YTD Gain (Post-Trade)", f"$\{cg['Post-Trade YTD Gain']:,.2f\}"]]\
            tt = ax_t.table(cellText=t_rows, loc='upper center', cellLoc='left', bbox=[0, 0, 1, 0.8]); tt.auto_set_font_size(False); tt.set_fontsize(9)\
            pdf.savefig(fig, bbox_inches='tight'); plt.close(fig)\
\
            fig2 = plt.figure(figsize=(8.5, 11), dpi=300)\
            gs2 = gridspec.GridSpec(4, 1, height_ratios=[1.0, 4.5, 4.5, 0.5], hspace=0.2, left=0.08, right=0.92, top=0.92, bottom=0.08)\
            ax_h2 = fig2.add_subplot(gs2[0]); ax_h2.axis('off')\
            ax_h2.text(0, 0.8, "DETAILED TRADE ANALYSIS", fontsize=20, fontweight='bold', color=NAVY)\
            ax_h2.text(1, 0.8, "Savvy", fontsize=20, fontweight='black', color=NAVY, ha='right')\
            ax_h2.text(0, 0.5, f"Client: \{client_name\}", fontsize=10, color='#666666'); ax_h2.axhline(y=0.2, color=NAVY, linewidth=2)\
\
            for i, (d, t, c) in enumerate([(buys, "TOP 5 BUYS", GREEN), (sells, "TOP 5 SELLS", RED)]):\
                ax_tbl = fig2.add_subplot(gs2[i+1]); ax_tbl.axis('off')\
                ax_tbl.text(0, 1.0, t, fontsize=12, fontweight='bold', color=c)\
                if not d.empty:\
                    d_rows = [[f"Acct (***\{r['Acct4']\})", r['Ticker'], textwrap.fill(r['Security Name'], 40), f"$\{abs(r['Trade $']):,.2f\}"] for _, r in d.iterrows()]\
                    tb = ax_tbl.table(cellText=d_rows, colLabels=['Account', 'Ticker', 'Security', 'Trade Amount'], loc='upper center', cellLoc='left', bbox=[0, 0, 1, 0.9])\
                    tb.auto_set_font_size(False); tb.set_fontsize(9)\
                    for (r, col), cell in tb.get_celld().items():\
                        cell.set_edgecolor('#e0e0e0')\
                        if r==0: cell.set_facecolor(c); cell.set_text_props(color='white', weight='bold', ha='center')\
                        else:\
                            if col in [0,1]: cell.get_text().set_ha('center'); \
                            if col==3: cell.get_text().set_ha('right')\
                else: ax_tbl.text(0.5, 0.5, "No Trades", ha='center', color='#999')\
            pdf.savefig(fig2, bbox_inches='tight'); plt.close(fig2)\
\
        buffer.seek(0)\
        return buffer, None\
    except Exception as e:\
        return None, str(e)\
\
st.title("Savvy Transition Analysis Tool")\
st.markdown("Internal Tool for Investment Team. Upload **Orion Export**.")\
\
with st.form("main_form"):\
    c_name = st.text_input("Client Name", placeholder="e.g. John Doe")\
    uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])\
    submitted = st.form_submit_button("Generate PDF Report")\
\
if submitted:\
    if not c_name or not uploaded_file:\
        st.error("Please fill in all fields.")\
    else:\
        with st.spinner("Processing..."):\
            pdf_bytes, error = generate_savvy_pdf(uploaded_file, c_name)\
            if error:\
                st.error(f"Error: \{error\}")\
            else:\
                st.success("Success!")\
                st.download_button(label="Download PDF", data=pdf_bytes, file_name=f"Savvy_Transition_\{c_name.replace(' ', '_')\}.pdf", mime="application/pdf")}