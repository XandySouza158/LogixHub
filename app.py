import base64
from datetime import datetime
from io import BytesIO
import uuid
import boto3
from boto3.dynamodb.conditions import Attr
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(page_title="LogixHub", page_icon="📦", layout="wide")

st.markdown("""
<style>
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #00BFFF !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #00BFFF !important;
}

[data-testid="stRadio"] div[role="radiogroup"] label div[aria-checked="true"] {
    background-color: #00BFFF !important;
}
[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] p {
    color: #00BFFF !important;
}

button[kind="primary"] {
    background-color: #00BFFF !important;
    border-color: #00BFFF !important;
    color: #0F172A !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def conectar_aws():
    try: return boto3.resource('dynamodb', region_name='us-east-2')
    except: return None

dynamodb = conectar_aws()
tabela_usuarios = dynamodb.Table('logixhub_usuarios') if dynamodb else None
tabela_mov = dynamodb.Table('logixhub_movimentacoes') if dynamodb else None

for k, v in [('logado', False), ('usuario', ''), ('perfil', ''), ('nome_completo', ''), ('foto_saida', None), ('foto_dev', None)]:
    if k not in st.session_state: st.session_state[k] = v

def autenticar_usuario(u, s):
    if not tabela_usuarios: return False
    try:
        resp = tabela_usuarios.get_item(Key={'username': u})
        if 'Item' in resp and resp['Item'].get('senha') == s:
            st.session_state.update({'logado': True, 'usuario': resp['Item']['username'], 'perfil': resp['Item']['perfil'], 'nome_completo': resp['Item'].get('nome', u)})
            return True
        return False
    except: return False

def fazer_logout():
    st.session_state.update({'logado': False, 'usuario': '', 'perfil': '', 'nome_completo': '', 'foto_saida': None, 'foto_dev': None})

def converter_imagem_para_base64(arq):
    try:
        img = Image.open(arq)
        img.thumbnail((550, 550))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

@st.dialog("📸 Câmera - Saída de Item")
def abrir_modal_camera_saida():
    st.write("Posicione o item e clique em tirar foto.")
    if (f := st.camera_input("Capturar")) is not None:
        st.session_state['foto_saida'] = f
        st.success("Foto capturada!")
        if st.button("Confirmar e Fechar", type="primary"): st.rerun()

@st.dialog("📸 Câmera - Devolução de Item")
def abrir_modal_camera_dev():
    st.write("Posicione o item devolvido e clique em tirar foto.")
    if (f := st.camera_input("Capturar Devolução")) is not None:
        st.session_state['foto_dev'] = f
        st.success("Foto capturada!")
        if st.button("Confirmar e Fechar", type="primary"): st.rerun()

if not st.session_state['logado']:
    st.markdown("""
    <style>
    [data-testid="stMain"] {
        background-image: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.85)), url("https://i.postimg.cc/yNFzYP4s/fundo-eaata-app.jpg");
        background-size: cover; background-position: center; background-repeat: no-repeat;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>📦 LogixHub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Controle Inteligente de Ativos e Logística</p>", unsafe_allow_html=True)
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        modo = st.radio("Ação", ["🔑 Entrar no Sistema", "📝 Criar conta"], horizontal=True, label_visibility="collapsed")
        st.divider()
        if "Entrar" in modo:
            st.subheader("Acesse sua conta")
            with st.form("form_login"):
                u = st.text_input("Usuário")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary"):
                    if autenticar_usuario(u, s): st.success("Login com sucesso!"); st.rerun()
                    else: st.error("Usuário ou senha incorretos.")
        else:
            st.subheader("Criar conta")
            with st.form("form_autocadastro"):
                nu = st.text_input("Nome de Usuário")
                ne = st.text_input("E-mail")
                ns = st.text_input("Senha", type="password")
                nn = st.text_input("Nome Completo")
                if st.form_submit_button("Registrar", type="primary"):
                    if nu and ne and ns and nn:
                        try:
                            if 'Item' in tabela_usuarios.get_item(Key={'username': nu}): st.error("Usuário já existe.")
                            elif tabela_usuarios.scan(FilterExpression=Attr('email').eq(ne))['Items']: st.error("E-mail já cadastrado.")
                            else:
                                tabela_usuarios.put_item(Item={'username': nu, 'email': ne, 'senha': ns, 'nome': nn, 'perfil': 'comum'})
                                st.success("Conta criada! Vá para 'Entrar'.")
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("Preencha tudo.")
else:
    st.sidebar.title(f"Olá, {st.session_state['nome_completo']} 👋")
    st.sidebar.write(f"Perfil: **{st.session_state['perfil'].upper()}**")
    st.sidebar.divider()
    
    pag = "📦 Operações do Sistema"
    if st.session_state['perfil'] == 'admin':
        st.sidebar.subheader("Menu Admin")
        pag = st.sidebar.radio("Nav", ["📦 Operações do Sistema", "📊 Dashboard de Movimentações"], label_visibility="collapsed")
        st.sidebar.divider()
    
    if st.sidebar.button("Sair (Logout)"): fazer_logout(); st.rerun()

    try: dados_banco = tabela_mov.scan()['Items'] if tabela_mov else []
    except: dados_banco = []

    if pag == "📊 Dashboard de Movimentações":
        st.title("📊 Dashboard Executivo - LogixHub")
        st.divider()
        if not dados_banco: st.info("Sem movimentações registradas.")
        else:
            df = pd.DataFrame(dados_banco)
            df_v = df[df['item'] == 'Veículo'] if 'item' in df.columns else pd.DataFrame()
            df_e = df[df['item'] == 'Equipamento'] if 'item' in df.columns else pd.DataFrame()
            sv, dv = len(df_v[df_v['acao'] == 'Saída']) if not df_v.empty else 0, len(df_v[df_v['acao'] == 'Devolução']) if not df_v.empty else 0
            se, de = len(df_e[df_e['acao'] == 'Saída']) if not df_e.empty else 0, len(df_e[df_e['acao'] == 'Devolução']) if not df_e.empty else 0
            
            st.subheader("🚗 Veículos")
            c1, c2, c3 = st.columns(3)
            c1.metric("Saídas", sv); c2.metric("Devoluções", dv); c3.metric("Na Rua", sv - dv)
            st.markdown("---")
            st.subheader("📦 Equipamentos")
            c4, c5, c6 = st.columns(3)
            c4.metric("Saídas", se); c5.metric("Devoluções", de); c6.metric("Fora", se - de)
            st.markdown("---")
            df_g = df.groupby(['item', 'acao']).size().unstack(fill_value=0)
            for col in ['Saída', 'Devolução']: 
                if col not in df_g.columns: df_g[col] = 0
            st.bar_chart(df_g[['Saída', 'Devolução']])
    else:
        st.title("Painel LogixHub")
        t_saida, t_dev, t_ger = st.tabs(["📤 Registrar Saída", "📥 Registrar Devolução", "⚙️ Gerenciamento"])
        
        with t_saida:
            st.header("Registrar Saída")
            ts = st.selectbox("Tipo", ["Veículo", "Equipamento"], key="ts")
            met_s = st.radio("Foto", ["📸 Tirar foto", "📁 Upload"], key="ms")
            foto_s = None
            if "Tirar" in met_s:
                if st.button("Abrir Câmera", key="cs"): abrir_modal_camera_saida()
                if st.session_state['foto_saida']:
                    st.success("Foto pronta!")
                    st.image(st.session_state['foto_saida'], width=350)
                    foto_s = st.session_state['foto_saida']
            else:
                st.session_state['foto_saida'] = None
                foto_s = st.file_uploader("Arquivo", type=["jpg", "jpeg", "png"], key="ups")
            
            if st.button("Confirmar Saída", type="primary"):
                if foto_s:
                    b64 = converter_imagem_para_base64(foto_s)
                    if b64:
                        try:
                            tabela_mov.put_item(Item={'id': str(uuid.uuid4()), 'acao': 'Saída', 'item': ts, 'usuario': st.session_state['usuario'], 'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'imagem_base64': b64})
                            st.session_state['foto_saida'] = None
                            st.success("Saída registrada!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Adicione uma foto.")

        with t_dev:
            st.header("Registrar Devolução")
            td = st.selectbox("Tipo", ["Veículo", "Equipamento"], key="td")
            met_d = st.radio("Foto", ["📸 Tirar foto", "📁 Upload"], key="md")
            foto_d = None
            if "Tirar" in met_d:
                if st.button("Abrir Câmera", key="cd"): abrir_modal_camera_dev()
                if st.session_state['foto_dev']:
                    st.success("Foto pronta!")
                    st.image(st.session_state['foto_dev'], width=350)
                    foto_d = st.session_state['foto_dev']
            else:
                st.session_state['foto_dev'] = None
                foto_d = st.file_uploader("Arquivo", type=["jpg", "jpeg", "png"], key="upd")
            
            if st.button("Confirmar Devolução", type="primary"):
                if foto_d:
                    b64 = converter_imagem_para_base64(foto_d)
                    if b64:
                        try:
                            tabela_mov.put_item(Item={'id': str(uuid.uuid4()), 'acao': 'Devolução', 'item': td, 'usuario': st.session_state['usuario'], 'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'imagem_base64': b64})
                            st.session_state['foto_dev'] = None
                            st.success("Devolução registrada!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Adicione uma foto.")

        with t_ger:
            st.header("Registros de Auditoria")
            st.write("---")
            if not dados_banco: st.info("Nenhum registro.")
            else:
                for mov in sorted(dados_banco, key=lambda x: x['data_hora'], reverse=True):
                    ico = "📤" if mov['acao'] == "Saída" else "📥"
                    st.markdown(f"{ico} **{mov['acao']}** | **Item:** {mov['item']} | **Usuário:** {mov['usuario']} | **Data:** {mov['data_hora']}")
                    if mov.get('imagem_base64'):
                        try: st.image(base64.b64decode(mov['imagem_base64']), width=400)
                        except: st.warning("Erro na imagem.")
                    if st.session_state['perfil'] == "admin":
                        if st.button("🗑️ Excluir", key=f"del_{mov['id']}"):
                            tabela_mov.delete_item(Key={'id': mov['id']})
                            st.rerun()
                    st.divider()