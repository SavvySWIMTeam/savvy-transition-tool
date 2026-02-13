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
            if found: dfs[key] = pd.read_excel(xlsx, sheet_name=found)
            else: return None, f"Missing sheet: {sheet_name}."

        mt_df, ht_df, gl_df, ac_df = dfs['Model Tolerance'], dfs['Holding and Trade Details'], dfs['Gain Loss Details'], dfs['Account and Cash Details']

        # 1. Model Name logic (Skip Unassigned)
        model_guesses = ht_df['Model Category'].dropna().unique()
        valid_models = [str(m).strip() for m in model_guesses if str(m).strip().lower() != 'unassigned']
        target_model = valid_models[0] if valid_models else "Savvy Strategic Model"

        # 2. Asset Allocation logic
        aa = mt_df[['Class', 'Current %', 'Target %', 'Trade $']].copy()
        for prefix in ['Savvy Total Portfolios - ', 'Savvy US Equity - ', 'Savvy Strategic 90/10 ', 'STP - Moderate Aggressive - ']:
            aa['Class'] = aa['Class'].str.replace(prefix, '', regex=False)
        aa['Class'] = aa['Class'].str.replace('U.S.', 'US', regex=False).str.strip()
        aa['Change %'] = aa['Target %'] - aa['Current %']
        aa = aa.sort_values('Target %', ascending=False).reset_index(drop=True)
        
        cash_idx = aa[aa['Class'].str.contains('Cash', case=False)].index
        if not cash_idx.empty: aa.loc[cash_idx[0], 'Class'] = 'Cash Equivalents'

        # 3. Trades logic
        trades = ht_df[ht_df['Trade $'].notna() & (ht_df['Trade $'] != 0)].copy()
        trades = trades[~trades['Ticker'].astype(str).str.contains('CUSTODIAL_CASH', case=False, na=False)]
        trades['abs_trade'] = trades['Trade $'].abs()
        trades['Acct4'] = trades['Account Number'].astype(str).str.split('.').str[0].str[-4:]
        
        if 'Trade G/L $' not in trades.columns: trades['Trade G/L $'] = 0.0
        trades['Trade G/L $'] = trades['Trade G/L $'].fillna(0)

        buys = trades[trades['Trade $'] > 0].sort_values('abs_trade', ascending=False).head(5)
        sells = trades[trades['Trade $'] < 0].sort_values('abs_trade', ascending=False).head(5)

        # 4. Financials
        cg, total_val = gl_df.iloc[0], ac_df['Account Value'].sum()

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
            gs = gridspec.GridSpec(6, 1, height_ratios=[1.2, 1.0, 0.2, 5.5, 1.8, 0.3], hspace=0.15, left=0.08, right=0.92, top=0.92, bottom=0.12)
            
            ax_h = fig.add_subplot(gs[0]); ax_h.axis('off')
            # Updated Font Size to 22 (10% tighter)
            ax_h.text(0, 0.8, "Portfolio Transition Analysis", fontsize=22, fontweight='bold', color=NAVY)
            ax_h.text(0, 0.5, f"CLIENT: {client_name.upper()}", fontsize=10, fontweight='bold', color='#444444')
            ax_h.text(0, 0.3, f"TARGET MODEL: {target_model}", fontsize=10, color='#666666')
            ax_h.axhline(y=0.1, color=NAVY, linewidth=2)
            
            if logo_img:
                # Updated Logo Size (scaled down 20%)
                ax_logo = fig.add_axes([0.73, 0.87, 0.19, 0.05], anchor='NE', zorder=10)
                ax_logo.axis('off'); ax_logo.imshow(logo_img)
            else:
                ax_h.text(1, 0.8, "Savvy", fontsize=22, fontweight='black', color=NAVY, ha='right')

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
            rows = [[textwrap.fill(r['Class'], 30), f"{r['Current %']:.2f}%", f"{r['Target %']:.2f}%", f"{r['Change %']:+.2f}%", f"${r['Trade $']:,.2f}"] for _, r in aa.iterrows()]
            col_widths_aa = [0.40, 0.12, 0.12, 0.12, 0.24]
            table = ax_a.table(cellText=rows, colLabels=['Asset Class', 'Current %', 'Target %', 'Change %', 'Trade Amount'], loc='upper center', cellLoc='left', colWidths=col_widths_aa)
            table.auto_set_font_size(False); table.set_fontsize(9); table.scale(1, 2.2)

            for (r, c), cell in table.get_celld().items():
                cell.set_edgecolor('#e0e0e0'); cell.set_linewidth(0.5)
                if r == 0: cell.set_facecolor(NAVY); cell.set_text_props(color='white', weight='bold', ha='center')
                else:
                    if c in [1,2,3]: cell.get_text().set_ha('center')
                    if c==4: cell.get_text().set_ha('right')
                    if c in [3,4]:
                        val_str = str(rows[r-1][c]).replace('%','').replace('$','').replace(',','')
                        val = float(val_str)
                        if val != 0: cell.get_text().set_color(GREEN if val > 0 else RED); cell.get_text().set_weight('bold')

            # Tax Table
            ax_t = fig.add_subplot(gs[4]); ax_t.axis('off')
            ax_t.text(0, 1.0, "TAX & REALIZED GAIN DETAILS", fontsize=11, fontweight='bold', color=NAVY, transform=ax_t.transAxes)
            t_rows = [["Short-Term Gains", f"${cg['Trade Short Term Gain']:,.2f}"], ["Long-Term Gains", f"${cg['Trade Long Term Gain']:,.2f}"],
                      ["Total Realized Gain", f"${cg['Trade Total Gain $']:,.2f}"], ["YTD Gain (Post-Trade)", f"${cg['Post-Trade YTD Gain']:,.2f}"]]
            tt = ax_t.table(cellText=t_rows, loc='upper center', cellLoc='left', bbox=[0, 0, 1, 0.8]); tt.auto_set_font_size(False); tt.set_fontsize(9)
            pdf.savefig(fig); plt.close(fig)

            # --- PAGE 2 ---
            fig2 = plt.figure(figsize=(8.5, 11), dpi=300)
            gs2 = gridspec.GridSpec(4, 1, height_ratios=[1.0, 4.5, 4.5, 0.5], hspace=0.2, left=0.08, right=0.92, top=0.92, bottom=0.08)
            ax_h2 = fig2.add_subplot(gs2[0]); ax_h2.axis('off')
            ax_h2.text(0, 0.8, "DETAILED TRADE ANALYSIS", fontsize=20, fontweight='bold', color=NAVY)
            if logo_img:
                # Page 2 Logo adjustment
                ax_logo2 = fig2.add_axes([0.73, 0.87, 0.19, 0.05], anchor='NE', zorder=10)
                ax_logo2.axis('off'); ax_logo2.imshow(logo_img)
            else:
                ax_h2.text(1, 0.8, "Savvy", fontsize=20, fontweight='black', color=NAVY, ha='right')
            ax_h2.text(0, 0.5, f"Client: {client_name}", fontsize=10, color='#666666'); ax_h2.axhline(y=0.2, color=NAVY, linewidth=2)

            col_widths_p2 = [0.18, 0.12, 0.45, 0.25]
            for i, (data, title, color) in enumerate([(buys, "TOP 5 BUYS", GREEN), (sells, "TOP 5 SELLS", RED)]):
                ax = fig2.add_subplot(gs2[i+1]); ax.axis('off')
                ax.text(0, 1.0, title, fontsize=12, fontweight='bold', color=color)
                if not data.empty:
                    d_rows = []
                    for _, r in data.iterrows():
                        mask = f"Ending in {r['Acct4']}"
                        if title == "TOP 5 BUYS": d_rows.append([mask, r['Ticker'], textwrap.fill(r['Security Name'], 40), f"${abs(r['Trade $']):,.2f}"])
                        else: d_rows.append([mask, r['Ticker'], textwrap.fill(r['Security Name'], 40), f"${abs(r['Trade $']):,.2f}\n(GL: ${r['Trade G/L $']:,.2f})"])
                    
                    tb = ax.table(cellText=d_rows, colLabels=['Account', 'Ticker', 'Security', 'Trade Amount'], loc='upper center', cellLoc='left', colWidths=col_widths_p2)
                    tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 2.2)
                    for (r_idx, c_idx), cell in tb.get_celld().items():
                        cell.set_edgecolor('#e0e0e0')
                        if r_idx == 0: cell.set_facecolor(color); cell.set_text_props(color='white', weight='bold', ha='center')
                        else:
                            if c_idx in [0,1]: cell.get_text().set_ha('center')
                            if c_idx == 3:
                                cell.get_text().set_ha('right')
                                if title == "TOP 5 SELLS":
                                    gl_val = data.iloc[r_idx-1]['Trade G/L $']
                                    cell.get_text().set_color(GREEN if gl_val > 0 else RED); cell.get_text().set_weight('bold')
                else: ax.text(0.5, 0.5, "No identified trades", ha='center', color='#999')

            pdf.savefig(fig2); plt.close(fig2)

        buffer.seek(0)
        return buffer, None
    except Exception as e: return None, str(e)

# --- UI LAYOUT ---
st.title("Savvy Transition Analysis Tool")
st.markdown("Investment Team Portal | Orion Export Generator")
with st.form("main_form"):
    c_name = st.text_input("Client Name", placeholder="e.g. John Doe")
    logo_file = st.file_uploader("Upload Logo (Optional override)", type=['png', 'jpg', 'jpeg'])
    uploaded_file = st.file_uploader("Upload Orion Excel File", type=['xlsx'])
    submitted = st.form_submit_button("Generate Transition Analysis")

if submitted:
    if not c_name or not uploaded_file: st.error("Please fill in all fields.")
    else:
        with st.spinner("Generating Report"):
            pdf_bytes, error = generate_savvy_pdf(uploaded_file, c_name, logo_file)
            if error: st.error(f"Error: {error}")
            else:
                st.success("Report Generated Successfully")
                st.download_button(label="Download PDF Report", data=pdf_bytes, file_name=f"Savvy_Transition_{c_name.replace(' ', '_')}.pdf", mime="application/pdf")
