import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
DB = Path("data/restaurant.db")
DB.parent.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Fourchette Pilot",
    page_icon="🍴",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 5rem; max-width: 760px;}
h1 {font-size: 1.75rem !important; margin-bottom: .1rem !important;}
h2, h3 {margin-top: .7rem !important;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 16px;
    padding: 12px;
}
.stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] button {
    min-height: 48px;
    border-radius: 14px;
    font-weight: 650;
    width: 100%;
}
div[data-baseweb="input"] input {font-size: 16px !important;}
textarea {font-size: 16px !important;}
[data-testid="stNumberInput"] button {min-height: 42px;}
</style>
""", unsafe_allow_html=True)

def db():
    return sqlite3.connect(DB)

def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS daily(
          day TEXT PRIMARY KEY,
          revenue REAL NOT NULL DEFAULT 0,
          covers INTEGER NOT NULL DEFAULT 0,
          food REAL NOT NULL DEFAULT 0,
          drinks REAL NOT NULL DEFAULT 0,
          waste REAL NOT NULL DEFAULT 0,
          labor_hours REAL NOT NULL DEFAULT 0,
          notes TEXT NOT NULL DEFAULT ''
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings(
          key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        defaults = {
            "restaurant_name":"La Fourchette",
            "target_ticket":"31",
            "target_cost_pct":"30",
            "monthly_rent":"1200",
            "monthly_payroll":"9000"
        }
        for k,v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings VALUES (?,?)",(k,v))

def get_settings():
    with db() as c:
        return dict(c.execute("SELECT key,value FROM settings").fetchall())

def set_setting(k,v):
    with db() as c:
        c.execute("""INSERT INTO settings(key,value) VALUES (?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(k,str(v)))

def get_data():
    with db() as c:
        df = pd.read_sql_query("SELECT * FROM daily ORDER BY day",c)
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df

def save_day(vals):
    with db() as c:
        c.execute("""INSERT INTO daily(day,revenue,covers,food,drinks,waste,labor_hours,notes)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(day) DO UPDATE SET
        revenue=excluded.revenue,covers=excluded.covers,food=excluded.food,
        drinks=excluded.drinks,waste=excluded.waste,labor_hours=excluded.labor_hours,
        notes=excluded.notes""",vals)

def euro(x):
    return f"{x:,.0f} €".replace(","," ")

def metrics(d):
    rev = float(d.revenue.sum()) if not d.empty else 0
    cov = int(d.covers.sum()) if not d.empty else 0
    costs = float((d.food+d.drinks+d.waste).sum()) if not d.empty else 0
    ticket = rev/cov if cov else 0
    ratio = 100*costs/rev if rev else 0
    return rev,cov,costs,ticket,ratio

def recs(d,cfg):
    if d.empty:
        return ["Saisis ton premier service pour commencer l'analyse."]
    rev,cov,costs,ticket,ratio = metrics(d.tail(14))
    target_ticket=float(cfg["target_ticket"])
    target_cost=float(cfg["target_cost_pct"])
    out=[]
    if ticket < target_ticket*.95:
        out.append(f"Ticket moyen : {euro(ticket)}. Tester une action simple pour augmenter les ventes additionnelles.")
    elif ticket > target_ticket*1.05:
        out.append(f"Ticket moyen : {euro(ticket)}, supérieur à la cible de {euro(target_ticket)}. Identifier les produits qui expliquent cette hausse.")
    else:
        out.append(f"Ticket moyen : {euro(ticket)}, proche de la cible de {euro(target_ticket)}.")
    if ratio > target_cost+3:
        out.append(f"Achats + pertes : {ratio:.1f}% du CA, au-dessus de la cible de {target_cost:.1f}%. Contrôler portions, pertes et prix fournisseurs.")
    else:
        out.append(f"Achats + pertes : {ratio:.1f}% du CA récent.")
    waste=float(d.tail(14).waste.sum())
    if rev and waste/rev > .02:
        out.append(f"Pertes déclarées : {100*waste/rev:.1f}% du CA récent. Noter les produits principalement concernés.")
    return out

def ai_analysis(df,cfg):
    key=os.getenv("OPENAI_API_KEY","").strip()
    try:
        key = st.secrets.get("OPENAI_API_KEY", key)
    except Exception:
        pass
    if not key:
        return "Analyse IA non configurée. Les recommandations automatiques fonctionnent sans clé API."
    from openai import OpenAI
    client=OpenAI(api_key=key)
    rows=df.tail(30).copy()
    rows["day"]=rows["day"].astype(str)
    prompt=f"""Analyse ces données de restaurant en français.
Paramètres: {cfg}
Données: {rows.to_dict(orient='records')}
Réponds de façon courte et pratique pour un restaurateur sur téléphone:
- 3 constats chiffrés
- 3 actions testables
- 1 point à surveiller
Signale clairement les limites des données. Ne présente pas une estimation comme une certitude."""
    r=client.responses.create(model=os.getenv("OPENAI_MODEL","gpt-5.6-luna"),input=prompt)
    return r.output_text

init()
cfg=get_settings()
df=get_data()

st.title("🍴 Fourchette Pilot")
st.caption("Pilotage quotidien du restaurant")

tab_home, tab_add, tab_history, tab_ai, tab_settings = st.tabs(
    ["Accueil","Saisir","Historique","Analyse","Réglages"]
)

with tab_home:
    period=st.segmented_control("Période",[7,14,30,90],default=30,format_func=lambda x:f"{x} j")
    cutoff=pd.Timestamp(date.today()-timedelta(days=int(period)-1))
    d=df[df.day>=cutoff] if not df.empty else df
    rev,cov,costs,ticket,ratio=metrics(d)
    c1,c2=st.columns(2)
    c1.metric("CA",euro(rev))
    c2.metric("Couverts",str(cov))
    c3,c4=st.columns(2)
    c3.metric("Ticket moyen",euro(ticket))
    c4.metric("Achats + pertes",f"{ratio:.1f}%")
    if not d.empty:
        st.line_chart(d.set_index("day")["revenue"],height=220)
    st.subheader("À regarder")
    for r in recs(d,cfg):
        st.info(r)

with tab_add:
    st.subheader("Service du soir")
    with st.form("quick",clear_on_submit=False):
        day=st.date_input("Date",date.today())
        revenue=st.number_input("CA du service (€)",min_value=0.0,step=50.0)
        covers=st.number_input("Couverts",min_value=0,step=1)
        st.markdown("**Coûts du jour**")
        food=st.number_input("Achats nourriture (€)",min_value=0.0,step=10.0)
        drinks=st.number_input("Achats boissons (€)",min_value=0.0,step=10.0)
        waste=st.number_input("Pertes / gaspillage (€)",min_value=0.0,step=5.0)
        hours=st.number_input("Heures équipe",min_value=0.0,step=.5)
        notes=st.text_area("Note rapide",placeholder="Événement, météo, rupture, groupe...")
        submitted=st.form_submit_button("Enregistrer le service",type="primary")
    if submitted:
        save_day((day.isoformat(),revenue,covers,food,drinks,waste,hours,notes))
        st.success("Service enregistré.")
        st.rerun()

with tab_history:
    st.subheader("Historique")
    if df.empty:
        st.info("Aucun service enregistré.")
    else:
        view=df.sort_values("day",ascending=False).copy()
        view["ticket"]=view.apply(lambda x:x.revenue/x.covers if x.covers else 0,axis=1)
        display=view[["day","revenue","covers","ticket","waste"]].copy()
        display.columns=["Date","CA","Couverts","Ticket","Pertes"]
        st.dataframe(display,use_container_width=True,hide_index=True,height=360)
        csv=view.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Exporter en CSV",csv,"fourchette_historique.csv","text/csv")

with tab_ai:
    st.subheader("Analyse")
    for r in recs(df,cfg):
        st.info(r)
    if st.button("Lancer l'analyse IA",type="primary"):
        if df.empty:
            st.warning("Il faut d'abord enregistrer quelques services.")
        else:
            with st.spinner("Analyse..."):
                try:
                    st.markdown(ai_analysis(df,cfg))
                except Exception as e:
                    st.error("L'analyse IA n'a pas pu être générée.")
                    st.caption(str(e))

with tab_settings:
    st.subheader("Réglages")
    with st.form("cfg"):
        name=st.text_input("Restaurant",cfg["restaurant_name"])
        ticket=st.number_input("Ticket cible (€)",min_value=0.0,value=float(cfg["target_ticket"]))
        cost=st.number_input("Cible achats + pertes (%)",min_value=0.0,max_value=100.0,value=float(cfg["target_cost_pct"]))
        rent=st.number_input("Loyer mensuel (€)",min_value=0.0,value=float(cfg["monthly_rent"]))
        payroll=st.number_input("Salaires + charges mensuels (€)",min_value=0.0,value=float(cfg["monthly_payroll"]))
        saved=st.form_submit_button("Sauvegarder")
    if saved:
        for k,v in {"restaurant_name":name,"target_ticket":ticket,"target_cost_pct":cost,
                    "monthly_rent":rent,"monthly_payroll":payroll}.items():
            set_setting(k,v)
        st.success("Réglages enregistrés.")
        st.rerun()
