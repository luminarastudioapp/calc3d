import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.title("🎲 3D Calc Pro")
st.caption("Precificação Inteligente para Impressão 3D e Resina")

# Extrai o ID do Google Sheets de qualquer formato de link
def get_spreadsheet_id(url):
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None

# Lê a aba diretamente via CSV público do Google
def load_google_sheet(sheet_id, sheet_name):
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(csv_url)

# Tabelas Padrão (Usadas se o link não for colado ou falhar)
default_materiais = pd.DataFrame([
    {"nome": "PLA", "preco_kg": 110.0},
    {"nome": "PETG", "preco_kg": 125.0},
    {"nome": "ABS", "preco_kg": 100.0},
    {"nome": "RESINA", "preco_kg": 180.0}
])

default_impressoras = pd.DataFrame([
    {"nome": "Ender 3 / V2", "watts": 130, "preco_maquina": 1800.0, "vida_util_h": 4000},
    {"nome": "Bambu A1", "watts": 150, "preco_maquina": 3600.0, "vida_util_h": 5000},
    {"nome": "Bambu X1C", "watts": 350, "preco_maquina": 11000.0, "vida_util_h": 6000},
    {"nome": "Impressora Resina", "watts": 60, "preco_maquina": 2500.0, "vida_util_h": 3000}
])

# Menu Lateral
st.sidebar.header("🔗 Conexão Google Sheets")
url_input = st.sidebar.text_input("Link da Planilha:", placeholder="Cole o link da sua planilha aqui...")

sheet_id = get_spreadsheet_id(url_input) if url_input else None

df_materiais = default_materiais
df_impressoras = default_impressoras

if sheet_id:
    try:
        df_mat_temp = load_google_sheet(sheet_id, "Materiais")
        df_imp_temp = load_google_sheet(sheet_id, "Impressoras")
        
        if 'nome' in df_mat_temp.columns and 'preco_kg' in df_mat_temp.columns:
            df_materiais = df_mat_temp
        if 'nome' in df_imp_temp.columns and 'watts' in df_imp_temp.columns:
            df_impressoras = df_imp_temp
            
        st.sidebar.success("✅ Conectado ao Google Sheets!")
    except Exception:
        st.sidebar.warning("⚠️ Não foi possível ler as abas 'Materiais' ou 'Impressoras'. Usando valores padrão.")
else:
    st.sidebar.info("💡 Usando tabela padrão. Cole o link da sua planilha acima para sincronizar seus preços.")

st.sidebar.divider()
st.sidebar.subheader("⚙️ Custos Operacionais")
kwh_cost = st.sidebar.number_input("Custo Energia (R$ / kWh)", value=1.25, step=0.05)

# Interface da Calculadora
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 Parâmetros do Projeto")
    proj_name = st.text_input("Nome do Projeto", value="Vaso Geométrico 3D")
    qty = st.number_input("Quantidade de Peças", min_value=1, value=1)

    printer_selected = st.selectbox("Selecione a Impressora", df_impressoras['nome'].dropna().tolist())
    printer_info = df_impressoras[df_impressoras['nome'] == printer_selected].iloc[0]

    mat_selected = st.selectbox("Selecione o Material", df_materiais['nome'].dropna().tolist())
    mat_info = df_materiais[df_materiais['nome'] == mat_selected].iloc[0]

    mat_cost_per_kg = st.number_input("Custo/KG do Material (R$)", value=float(mat_info['preco_kg']))

    col_w, col_t = st.columns(2)
    with col_w:
        weight_g = st.number_input("Peso Total (g)", min_value=0.0, value=85.0, step=5.0)
    with col_t:
        hours = st.number_input("Tempo (Horas)", min_value=0, value=4)
        mins = st.number_input("Tempo (Minutos)", min_value=0, max_value=59, value=30)

    markup = st.slider("Margem de Lucro / Markup (%)", min_value=20, max_value=300, value=100, step=10)

# Cálculos
total_hours = hours + (mins / 60)
cost_mat = (weight_g / 1000) * mat_cost_per_kg
cost_energy = (float(printer_info['watts']) / 1000) * total_hours * kwh_cost
cost_depr = (float(printer_info['preco_maquina']) / max(1, float(printer_info['vida_util_h']))) * total_hours

total_cost = cost_mat + cost_energy + cost_depr
final_price = total_cost * (1 + (markup / 100))
profit = final_price - total_cost

with col2:
    st.subheader("📊 Demonstrativo de Orçamento")
    
    if weight_g > 0 and total_hours > 0:
        st.metric(label="💰 PREÇO DE VENDA SUGERIDO", value=f"R$ {final_price:.2f}", delta=f"Lucro Limpo: R$ {profit:.2f}")
        
        if qty > 1:
            st.caption(f"Valor por unidade ({qty} un): **R$ {final_price/qty:.2f}**")
            
        st.divider()
        
        df_detalhes = pd.DataFrame({
            "Componente": ["Material (Filamento/Resina)", "Energia Elétrica", "Depreciação Máquina", "Lucro Bruto"],
            "Valor (R$)": [cost_mat, cost_energy, cost_depr, profit]
        })
        st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)
        st.bar_chart(df_detalhes.set_index("Componente"))

        wsp_text = f"*Orçamento 3D — {proj_name}*\n\n📦 Quantidade: {qty} un\n💰 Valor Total: R$ {final_price:.2f}\n\n✅ Garantia de Qualidade."
        st.text_area("Texto formatado para WhatsApp:", value=wsp_text, height=100)
    else:
        st.info("Preencha o peso e o tempo para calcular.")
