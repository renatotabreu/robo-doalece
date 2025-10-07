# ==============================================================================
# SCRIPT COMPLETO PARA monitor_tjce.py
# Robô para buscar, baixar e enviar o Diário da Justiça Eletrônico (TJCE)
# Adaptado para GitHub Actions
# ==============================================================================

import requests
import datetime
import os
import smtplib
import mimetypes
import traceback
import fitz  # PyMuPDF
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup

# ==============================================================================
# SEÇÃO DE CONFIGURAÇÃO DE E-MAIL (LENDO SECRETS DO GITHUB)
# ==============================================================================
email_remetente = os.environ.get("GMAIL_USER")
senha_remetente = os.environ.get("GMAIL_PASSWORD")
destinatarios_str = os.environ.get("DESTINATARIOS")
cadernos_str = os.environ.get("TJCE_CADERNOS")

# Verifica se todas as secrets foram carregadas
if not all([email_remetente, senha_remetente, destinatarios_str, cadernos_str]):
    print("ERRO CRÍTICO: Uma ou mais secrets (GMAIL_USER, GMAIL_PASSWORD, DESTINATARIOS, TJCE_CADERNOS) não foram definidas.")
    exit()

# Converte as strings das secrets em listas
lista_destinatarios = [email.strip() for email in destinatarios_str.split(',')]
lista_cadernos_ids = [int(caderno.strip()) for caderno in cadernos_str.split(',')]

smtp_servidor = "smtp.gmail.com"
smtp_porta = 587
# ==============================================================================

# Funções de extração de texto e envio de e-mail (são as mesmas do script anterior)
def extrair_conteudo_formatado(caminho_arquivo_pdf):
    try:
        texto_completo = ""
        with fitz.open(caminho_arquivo_pdf) as doc:
            for page in doc:
                texto_completo += page.get_text("text", sort=True) + "\n"
        texto_final = texto_completo.strip()
        if not texto_final: return "Não foi possível extrair o conteúdo do Diário.\n"
        return f"📰 CONTEÚDO DO DIÁRIO DE JUSTIÇA: 📰\n\n{texto_final}"
    except Exception as e:
        print(f"  - ERRO GRAVE ao processar o arquivo PDF: {e}")
        traceback.print_exc()
        return "Ocorreu um erro grave ao tentar ler o arquivo PDF.\n"

def enviar_email_com_anexo(caminho_anexo, data_diario_formatada, nome_caderno, texto_publicacoes):
    assunto = f"⚖️🔵 DJE-TJCE de {data_diario_formatada} ({nome_caderno}) 📅"
    if not lista_destinatarios:
        print("⚠️ A lista de destinatários está vazia.")
        return
    print(f"📧 Preparando para enviar e-mail para {len(lista_destinatarios)} destinatário(s)...")
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Robô DJE-TJCE <{email_remetente}>"
        msg['Subject'] = assunto
        corpo = (f"🤖 Olá,\n\n"
                 f"Segue em anexo o arquivo PDF do Diário da Justiça Eletrônico do Ceará de {data_diario_formatada} ({nome_caderno}).\n\n"
                 f"Abaixo, o conteúdo extraído do documento para consulta rápida.\n\n"
                 f"{'='*84}\n\n{texto_publicacoes}\n\n{'='*83}\n\n"
                 f"Atenciosamente,\n\n🤖 Robô extraoficial de notificações do DJE-TJCE ⚖️")
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        ctype, _ = mimetypes.guess_type(caminho_anexo)
        if ctype is None: ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(caminho_anexo, 'rb') as fp:
            part = MIMEBase(maintype, subtype)
            part.set_payload(fp.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_anexo))
        msg.attach(part)
        
        servidor = smtplib.SMTP(smtp_servidor, smtp_porta)
        servidor.starttls()
        servidor.login(email_remetente, senha_remetente)
        servidor.send_message(msg, to_addrs=lista_destinatarios)
        servidor.quit()
        print("✅ E-mail enviado com sucesso!")
    except Exception as e:
        print(f"\n❌ ERRO DE E-MAIL: {e}")
        traceback.print_exc()

# ==============================================================================
# FUNÇÃO PRINCIPAL PARA O TJCE
# ==============================================================================
def baixar_diario_tjce_mais_recente():
    diretorio_downloads = "diarios_justica_ce"
    if not os.path.exists(diretorio_downloads): os.makedirs(diretorio_downloads)
    
    # Mapeamento de IDs para nomes dos cadernos
    mapa_cadernos = {
        1: "Administrativo", 2: "Judicial 1ª Instância", 3: "Judicial 2ª Instância",
        4: "Editais 1ª Instância", 5: "Editais 2ª Instância"
    }

    # Loop para buscar nos últimos 7 dias
    for i in range(7):
        data_pesquisa = datetime.date.today() - datetime.timedelta(days=i)
        data_formatada = data_pesquisa.strftime('%d/%m/%Y')
        
        # Loop pelos cadernos definidos na secret, em ordem de prioridade
        for caderno_id in lista_cadernos_ids:
            nome_caderno = mapa_cadernos.get(caderno_id, f"Caderno_{caderno_id}")
            print(f"🔍 Buscando DJE para data: {data_formatada}, Caderno: {nome_caderno}...")

            url_busca = "https://esaj.tjce.jus.br/cdje/search.do"
            params = {'dados.dtDiario': data_formatada, 'cdCaderno': caderno_id}

            try:
                resposta_html = requests.get(url_busca, params=params, timeout=30)
                resposta_html.raise_for_status()
                soup = BeautifulSoup(resposta_html.text, 'html.parser')
                link_download = soup.select_one('ul.list-unstyled a[href*="download.do"]')

                if link_download:
                    print(f"  - ✅ Diário encontrado!")
                    url_completa_pdf = f"https://esaj.tjce.jus.br{link_download['href']}"
                    
                    print("  - Baixando o arquivo PDF...")
                    resposta_pdf = requests.get(url_completa_pdf, timeout=60)
                    resposta_pdf.raise_for_status()

                    nome_arquivo = f"DJE_TJCE_{data_pesquisa.strftime('%Y-%m-%d')}_{nome_caderno.replace(' ', '_')}.pdf"
                    caminho_arquivo = os.path.join(diretorio_downloads, nome_arquivo)

                    with open(caminho_arquivo, 'wb') as f:
                        f.write(resposta_pdf.content)
                    print(f"  - Arquivo salvo em: {caminho_arquivo}")
                    
                    print("  - Extraindo texto do PDF...")
                    texto_extraido = extrair_conteudo_formatado(caminho_arquivo)
                    
                    enviar_email_com_anexo(caminho_arquivo, data_formatada, nome_caderno, texto_extraido)
                    
                    # Se encontrou e enviou, encerra o script com sucesso
                    return

            except requests.exceptions.RequestException as e:
                print(f"  - ❌ Erro de conexão ao buscar o diário: {e}")
            except Exception as e:
                print(f"  - ❌ Ocorreu um erro inesperado: {e}")
                
    print("\nFim da busca. Nenhum diário foi encontrado nos últimos 7 dias para os cadernos especificados.")

if __name__ == "__main__":
    baixar_diario_tjce_mais_recente()
