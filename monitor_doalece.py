# ==============================================================================
# SCRIPT COMPLETO E FINALIZADO PARA monitor_doalece.py
# ADAPTADO PARA USO COM GITHUB ACTIONS E SECRETS
# ==============================================================================

import requests
import datetime
import os
import json
import smtplib
import mimetypes
import traceback
import fitz  # PyMuPDF
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ==============================================================================
# SEÇÃO DE CONFIGURAÇÃO DE E-MAIL (MODIFICADA PARA GITHUB ACTIONS)
# ==============================================================================
email_remetente = os.environ.get("GMAIL_USER")
senha_remetente = os.environ.get("GMAIL_PASSWORD")
destinatarios_str = os.environ.get("DESTINATARIOS") # Lê a lista do Secret

# Verifica se as credenciais foram carregadas
if not all([email_remetente, senha_remetente, destinatarios_str]):
    print("ERRO CRÍTICO: As secrets GMAIL_USER, GMAIL_PASSWORD e/ou DESTINATARIOS não foram definidas no repositório.")
    exit()

# Converte a string de e-mails (separada por vírgula) em uma lista de e-mails
lista_destinatarios = [email.strip() for email in destinatarios_str.split(',')]

smtp_servidor = "smtp.gmail.com"
smtp_porta = 587
# ==============================================================================


def extrair_conteudo_formatado(caminho_arquivo_pdf):
    """
    Extrai o conteúdo principal do Diário Oficial em PDF, removendo
    cabeçalho e rodapé para apresentar o texto de forma limpa e estruturada.
    """
    try:
        # Etapa 1: Extrair o texto completo preservando o layout
        texto_completo = ""
        with fitz.open(caminho_arquivo_pdf) as doc:
            for page in doc:
                texto_completo += page.get_text("text", sort=True) + "\n"

        # Etapa 2: Isolar o corpo principal do Diário
        
        # Remove o rodapé primeiro, se existir
        if "FIM DA PUBLICAÇÃO" in texto_completo:
            texto_completo = texto_completo.split("FIM DA PUBLICAÇÃO")[0]

        # Remove o cabeçalho
        marcador_fim_cabecalho = "Sávia Maria de Queiroz Magalhães"
        pos_marcador = texto_completo.find(marcador_fim_cabecalho)
        
        if pos_marcador != -1:
            # Encontra a próxima quebra de linha após o marcador para cortar o texto
            pos_quebra_linha = texto_completo.find('\n', pos_marcador)
            if pos_quebra_linha != -1:
                texto_completo = texto_completo[pos_quebra_linha:]

        # Limpeza final de espaços extras no início/fim
        texto_final = texto_completo.strip()

        if not texto_final:
            return "Não foi possível extrair o conteúdo principal do Diário.\n"

        return f"📰 CONTEÚDO DO DIÁRIO OFICIAL: 📰\n\n{texto_final}"

    except Exception as e:
        print(f"  - ERRO INESPERADO E GRAVE ao processar o arquivo PDF.")
        print(f"  - Tipo de Erro: {type(e).__name__}")
        print(f"  - Mensagem: {e}")
        print("  - Rastreamento completo do erro (Traceback):")
        traceback.print_exc()
        return "Ocorreu um erro grave e irrecuperável ao tentar ler o arquivo PDF.\n"

# ==============================================================================
# FUNÇÃO DE ENVIO DE E-MAIL
# ==============================================================================
def enviar_email_com_anexos(lista_de_caminhos_anexos, data_diario_formatada, info_edicao, texto_publicacoes):
    assunto = f"📰🟡 DOALECE de {data_diario_formatada} ({info_edicao}) 📅"
    
    # Verifica se a lista de destinatários não está vazia
    if not lista_destinatarios:
        print("⚠️ A lista de destinatários está vazia. Nenhum e-mail será enviado.")
        return

    print(f"📧 Preparando para enviar e-mail em cópia oculta para {len(lista_destinatarios)} destinatário(s)...")

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Robô DOALECE <{email_remetente}>"
        msg['Subject'] = assunto
        
        corpo = (f"🤖 Olá,\n\n"
                 f"Seguem em anexo os arquivos PDF e ODT do Diário Oficial da Assembleia Legislativa do Ceará de {data_diario_formatada} ({info_edicao}).\n\n"
                 f"Abaixo, segue o conteúdo extraído do documento para consulta rápida.\n\n"
                 f"{'='*84}\n\n")
        corpo += texto_publicacoes
        corpo += f"\n{'='*83}\n\n"
        corpo += "💡 Caso sinta falta de alguma publicação, por gentileza me informe para a melhoria contínua da minha atuação. 🦾\n\nAtenciosamente,\n\n🤖 Robô extraoficial de notificações do DOALECE 📄"
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        for caminho_anexo in lista_de_caminhos_anexos:
            nome_anexo = os.path.basename(caminho_anexo)
            ctype, encoding = mimetypes.guess_type(caminho_anexo)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            with open(caminho_anexo, 'rb') as fp:
                part = MIMEBase(maintype, subtype)
                part.set_payload(fp.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=nome_anexo)
            msg.attach(part)
            
        servidor = smtplib.SMTP(smtp_servidor, smtp_porta)
        servidor.starttls()
        servidor.login(email_remetente, senha_remetente)
        
        # O método send_message envia para a lista completa de destinatários
        servidor.send_message(msg, to_addrs=lista_destinatarios)
        
        servidor.quit()
        print("✅ E-mail enviado com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO DE E-MAIL: Não foi possível enviar o e-mail. Erro: {e}")
        traceback.print_exc()

def baixar_diario_mais_recente():
    url_busca_api = "https://doalece.al.ce.gov.br/api/publico/ultimas-edicoes"
    dominio_base = "https://doalece.al.ce.gov.br"
    headers = {'User-Agent': 'Mozilla/5.0'}
    diretorio_downloads = "diarios_oficiais_ce"
    if not os.path.exists(diretorio_downloads): os.makedirs(diretorio_downloads)
    
    data_atual = datetime.date.today()
    print(f"Iniciando busca a partir de: {data_atual.strftime('%d/%m/%Y')}")

    for i in range(30):
        data_pesquisa = data_atual - datetime.timedelta(days=i)
        data_formatada_api = data_pesquisa.strftime('%Y-%m-%d')
        print(f"🔍 Buscando publicação para a data: {data_formatada_api}...")
        try:
            params = {"buscarData": json.dumps({"data_de": data_formatada_api, "data_ate": data_formatada_api})}
            resposta_busca = requests.get(url_busca_api, params=params, headers=headers, timeout=20)
            resposta_busca.raise_for_status()
            resposta_json = resposta_busca.json()
            lista_publicacoes_api = resposta_json.get("dados")

            if lista_publicacoes_api:
                publicacao = lista_publicacoes_api[0]
                caminho_pdf_remoto = publicacao.get("caminho_documento_pdf")
                caminho_odt_remoto = publicacao.get("caminho_documento_odt")
                if not caminho_pdf_remoto or not caminho_odt_remoto:
                    print("  - Edição encontrada, mas sem arquivos PDF ou ODT disponíveis. Pulando.")
                    continue

                data_publicacao_str = publicacao.get("data_publicacao", data_formatada_api).split(" ")[0]
                info_edicao_str = publicacao.get("numero_identificacao", "") 
                print(f"✅ Publicação encontrada: {data_publicacao_str} - {info_edicao_str}")
                
                data_obj = datetime.datetime.strptime(data_publicacao_str, '%Y-%m-%d')
                data_formatada_email = data_obj.strftime('%d/%m/%Y')
                
                info_formatada_nome = info_edicao_str.replace(' ', '_').replace('/', '-')
                nome_base_arquivo = f"DOALECE_{data_publicacao_str}_{info_formatada_nome}"
                nome_arquivo_pdf = f"{nome_base_arquivo}.pdf"
                nome_arquivo_odt = f"{nome_base_arquivo}.odt"
                arquivos_baixados = []

                caminho_completo_pdf = os.path.join(diretorio_downloads, nome_arquivo_pdf)
                resposta_pdf = requests.get(f"{dominio_base}{caminho_pdf_remoto}", headers=headers, timeout=60)
                with open(caminho_completo_pdf, 'wb') as f: f.write(resposta_pdf.content)
                arquivos_baixados.append(caminho_completo_pdf)
                print(f"  - PDF baixado: {nome_arquivo_pdf}")
                
                caminho_completo_odt = os.path.join(diretorio_downloads, nome_arquivo_odt)
                resposta_odt = requests.get(f"{dominio_base}{caminho_odt_remoto}", headers=headers, timeout=60)
                with open(caminho_completo_odt, 'wb') as f: f.write(resposta_odt.content)
                arquivos_baixados.append(caminho_completo_odt)
                print(f"  - ODT baixado: {nome_arquivo_odt}")

                print("📖 Processando arquivo PDF para extração de conteúdo...")
                texto_todas_publicacoes = extrair_conteudo_formatado(caminho_completo_pdf)
                
                enviar_email_com_anexos(arquivos_baixados, data_formatada_email, info_edicao_str, texto_todas_publicacoes)
                
                return

        except requests.exceptions.RequestException as e:
            print(f"  - Erro de conexão ao buscar dados da API: {e}")
        except Exception as e:
            print(f"  - Ocorreu um erro inesperado: {e}")
            
    print("\nFim da busca. Nenhuma publicação foi encontrada nos últimos 30 dias.")

if __name__ == "__main__":
    baixar_diario_mais_recente()
