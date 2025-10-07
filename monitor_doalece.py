# (Dentro da função baixar_diario_mais_recente, dentro do if lista_publicacoes_api:)

if lista_publicacoes_api:
    publicacao = lista_publicacoes_api[0]
    caminho_pdf_remoto = publicacao.get("caminho_documento_pdf")
    caminho_odt_remoto = publicacao.get("caminho_documento_odt")
    
    if not caminho_pdf_remoto or not caminho_odt_remoto:
        print("  - Edição encontrada, mas sem arquivos PDF ou ODT. Pulando.")
        continue # Usa 'continue' para ir para o próximo dia no loop

    data_publicacao_str = publicacao.get("data_publicacao").split(" ")[0]
    info_edicao_str = publicacao.get("numero_identificacao", "")
    print(f"✅ Publicação encontrada: {data_publicacao_str} - {info_edicao_str}")
    
    # 1. Montar nomes dos arquivos locais
    data_obj = datetime.datetime.strptime(data_publicacao_str, '%Y-%m-%d')
    data_formatada_email = data_obj.strftime('%d/%m/%Y')
    info_formatada_nome = info_edicao_str.replace(' ', '_').replace('/', '-')
    nome_base_arquivo = f"DOALECE_{data_publicacao_str}_{info_formatada_nome}"
    
    arquivos_baixados = []

    # 2. Baixar o PDF
    nome_arquivo_pdf = f"{nome_base_arquivo}.pdf"
    caminho_completo_pdf = os.path.join(diretorio_downloads, nome_arquivo_pdf)
    resposta_pdf = requests.get(f"{dominio_base}{caminho_pdf_remoto}", headers=headers, timeout=60)
    with open(caminho_completo_pdf, 'wb') as f:
        f.write(resposta_pdf.content)
    arquivos_baixados.append(caminho_completo_pdf)
    print(f"  - PDF baixado: {nome_arquivo_pdf}")
    
    # 3. Baixar o ODT
    nome_arquivo_odt = f"{nome_base_arquivo}.odt"
    caminho_completo_odt = os.path.join(diretorio_downloads, nome_arquivo_odt)
    resposta_odt = requests.get(f"{dominio_base}{caminho_odt_remoto}", headers=headers, timeout=60)
    with open(caminho_completo_odt, 'wb') as f:
        f.write(resposta_odt.content)
    arquivos_baixados.append(caminho_completo_odt)
    print(f"  - ODT baixado: {nome_arquivo_odt}")

    # 4. Chamar a função de extração de texto
    print("📖 Processando arquivo PDF para extração de conteúdo...")
    texto_para_email = extrair_conteudo_formatado(caminho_completo_pdf)
    
    # 5. Chamar a função de envio de e-mail
    enviar_email_com_anexos(arquivos_baixados, data_formatada_email, info_edicao_str, texto_para_email)
    
    return # Para o script
