import base64
import time
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
        
        # Converte a imagem para RGB caso ela tenha fundo transparente (RGBA ou P)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
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

    # ==========================================
    # DASHBOARD
    # ==========================================
    if pag == "📊 Dashboard de Movimentações":
        st.title("📊 Dashboard Executivo - LogixHub")
        st.divider()
        if not dados_banco: st.info("Sem movimentações registradas.")
        else:
            df = pd.DataFrame(dados_banco)
            
            # ALTERAÇÃO 4: Aparecer perfis pendentes de devolução
            pendentes_dash = df[df.get('status') == 'Pendente'] if 'status' in df.columns else pd.DataFrame()
            if not pendentes_dash.empty:
                st.error("⚠️ Perfis com Devoluções Pendentes")
                st.dataframe(pendentes_dash[['usuario', 'item', 'data_hora', 'motivo']], hide_index=True, use_container_width=True)
                st.markdown("---")

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
        
        # Abas baseadas no perfil
        if st.session_state['perfil'] == 'admin':
            abas = st.tabs(["📤 Registrar Saída", "📥 Registrar Devolução", "⚙️ Gerenciamento"])
            t_saida, t_dev, t_ger = abas
        else:
            abas = st.tabs(["📤 Registrar Saída", "📥 Registrar Devolução"])
            t_saida, t_dev = abas[0], abas[1]
        
        # ==========================================
        # ABA 1: REGISTRAR SAÍDA
        # ==========================================
        with t_saida:
            st.header("Registrar Saída")
            
            # ALTERAÇÃO 5: Admin pode registrar saída em qualquer perfil
            if st.session_state['perfil'] == 'admin':
                usuario_alvo = st.text_input("Registrar saída em nome de qual usuário?", value=st.session_state['usuario'])
            else:
                usuario_alvo = st.session_state['usuario']

            ts = st.selectbox("Tipo", ["Veículo", "Equipamento"], key="ts")
            
            # ALTERAÇÃO 3: Campo de mensagem obrigatório
            motivo_s = st.text_area("Descrição e motivo do uso (Obrigatório):", key="motivo_saida")

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
                if not motivo_s.strip():
                    st.warning("⚠️ O campo de descrição/motivo é obrigatório!")
                elif foto_s:
                    b64 = converter_imagem_para_base64(foto_s)
                    if b64:
                        try:
                            # ALTERAÇÃO 2: Envia com status Pendente
                            tabela_mov.put_item(Item={
                                'id': str(uuid.uuid4()), 
                                'acao': 'Saída', 
                                'item': ts, 
                                'usuario': usuario_alvo, 
                                'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 
                                'imagem_base64': b64,
                                'motivo': motivo_s,
                                'status': 'Pendente'
                            })
                            st.session_state['foto_saida'] = None
                            st.success(f"Registrado com sucesso para {usuario_alvo}!")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Adicione uma foto (Obrigatório).")

        # ==========================================
        # ABA 2: REGISTRAR DEVOLUÇÃO
        # ==========================================
        with t_dev:
            st.header("Registrar Devolução")
            
            # ALTERAÇÃO 5 e 2: Filtra pendências (Admin vê tudo, usuário vê as dele)
            if st.session_state['perfil'] == 'admin':
                pendentes = [m for m in dados_banco if m.get('status') == 'Pendente']
            else:
                pendentes = [m for m in dados_banco if m.get('status') == 'Pendente' and m.get('usuario') == st.session_state['usuario']]

            if not pendentes:
                st.info("Nenhuma pendência encontrada.")
            else:
                opcoes_pend = {m['id']: f"{m['item']} - Retirado por: {m['usuario']} (Saída: {m['data_hora']})" for m in pendentes}
                item_devolver = st.selectbox("Selecione a pendência para dar baixa:", options=list(opcoes_pend.keys()), format_func=lambda x: opcoes_pend[x])
                
                # Puxa os dados originais do item selecionado para gravar no log de devolução
                mov_pendente = next(m for m in pendentes if m['id'] == item_devolver)
                td = mov_pendente['item']

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
                                # 1. Atualiza o status do item original de 'Pendente' para 'Devolvido'
                                tabela_mov.update_item(
                                    Key={'id': item_devolver},
                                    UpdateExpression="SET #st = :val",
                                    ExpressionAttributeNames={'#st': 'status'},
                                    ExpressionAttributeValues={':val': 'Devolvido'}
                                )
                                
                                # 2. Cria o log da devolução amarrado ao usuário que fez a baixa
                                tabela_mov.put_item(Item={
                                    'id': str(uuid.uuid4()), 
                                    'acao': 'Devolução', 
                                    'item': td, 
                                    'usuario': mov_pendente['usuario'], # Nome de quem retirou
                                    'baixado_por': st.session_state['usuario'], # Quem está logado dando a baixa
                                    'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 
                                    'imagem_base64': b64
                                })
                                st.session_state['foto_dev'] = None
                                st.success("Devolução concluída!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("Adicione uma foto (Obrigatório).")

        # ==========================================
        # ABA 3: GERENCIAMENTO (APENAS ADMIN)
        # ==========================================
        if st.session_state['perfil'] == 'admin':
            with t_ger:
                st.header("Registros de Auditoria")
                
                # ALTERAÇÃO 1: Barra de Pesquisa
                termo_pesquisa = st.text_input("🔍 Pesquisar em todos os registros (ID, Usuário, Item ou Motivo):")
                st.write("---")
                
                lista_exibicao = dados_banco
                if termo_pesquisa:
                    termo_low = termo_pesquisa.lower()
                    lista_exibicao = [m for m in dados_banco if any(termo_low in str(v).lower() for v in m.values())]

                if not lista_exibicao: 
                    st.info("Nenhum registro encontrado.")
                else:
                    for mov in sorted(lista_exibicao, key=lambda x: x['data_hora'], reverse=True):
                        ico = "📤" if mov['acao'] == "Saída" else "📥"
                        txt_motivo = f" | **Motivo:** {mov.get('motivo')}" if mov.get('motivo') else ""
                        txt_status = f" | **Status:** {mov.get('status')}" if mov.get('status') else ""
                        
                        st.markdown(f"{ico} **{mov['acao']}** | **Item:** {mov['item']} | **Usuário:** {mov['usuario']} | **Data:** {mov['data_hora']}{txt_motivo}{txt_status}")
                        
                        if mov.get('imagem_base64'):
                            try: st.image(base64.b64decode(mov['imagem_base64']), width=400)
                            except: st.warning("Erro na imagem.")
                        
                        colA, colB = st.columns([2, 8])
                        with colA:
                            if st.button("🗑️ Excluir", key=f"del_{mov['id']}"):
                                tabela_mov.delete_item(Key={'id': mov['id']})
                                st.rerun()
                                
                        # ALTERAÇÃO 1: Edição para o Admin
                        with st.expander(f"✏️ Editar Registro (ID: {mov['id'][:8]}...)"):
                            novo_motivo = st.text_area("Editar Motivo:", value=mov.get('motivo', ''), key=f"edit_m_{mov['id']}")
                            if st.button("Salvar Alteração", key=f"save_{mov['id']}", type="secondary"):
                                try:
                                    tabela_mov.update_item(
                                        Key={'id': mov['id']},
                                        UpdateExpression="SET motivo = :m",
                                        ExpressionAttributeValues={':m': novo_motivo}
                                    )
                                    st.success("Registro atualizado!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao atualizar: {e}")
                                
                        st.divider()