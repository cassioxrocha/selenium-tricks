from multiprocessing.connection import wait
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Verificar se as variáveis existem (foram passadas do app.py)
if 'uc' not in locals():
    uc = "10039814775"  # valor padrão para teste
if 'mes_ano' not in locals():
    mes_ano = "AGO/2025"  # valor padrão para teste
if 'documento' not in locals():
    documento = "70147558620"
if 'nome' not in locals():
    nome = "CASSIO XAVIER ROCHA"
if 'data_nascimento' not in locals():
    data_nascimento = "22/11/1968"

print(f"Parâmetros recebidos: UC={uc}, Mês/Ano={mes_ano}, Documento={documento}, Nome={nome}, Data de Nascimento={data_nascimento}")

options = Options()
options.add_argument('--ignore-ssl-errors=yes')
options.add_argument('--ignore-certificate-errors')

# Configurar pasta de downloads para uma pasta existente e mapeada
download_dir = "/tmp/downloads"
os.makedirs(download_dir, exist_ok=True)  # Criar pasta se não existir

# DEBUG: Verificar se a pasta foi criada
print(f"Pasta de downloads criada: {download_dir}")
print(f"Pasta existe: {os.path.exists(download_dir)}")

# Configurações mais robustas do Firefox para download
options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.download.dir", download_dir)
options.set_preference("browser.download.manager.showWhenStarting", False) 
options.set_preference("browser.download.useDownloadDir", True)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/x-pdf")
options.set_preference("browser.download.manager.alertOnEXEOpen", False)
options.set_preference("browser.download.manager.focusWhenStarting", False)
options.set_preference("browser.download.manager.useWindow", False)
options.set_preference("browser.download.manager.showAlertOnComplete", False)
options.set_preference("browser.download.manager.closeWhenDone", True)

print(f"Firefox configurado para baixar em: {download_dir}")

driver = webdriver.Remote("http://selenium:4444/wd/hub", options=options)

# Inicializar WebDriverWait
wait = WebDriverWait(driver, 10)

driver.get("https://goias.equatorialenergia.com.br/LoginGO.aspx")
time.sleep(3)
driver.set_window_size(1024, 768)
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtUC"))).send_keys(uc)
time.sleep(3)
driver.get_screenshot_as_file('print1.png')
wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtDocumento"))).send_keys(documento)
time.sleep(3)
driver.get_screenshot_as_file('print2.png')
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button:nth-child(2)"))).click()
time.sleep(3)
if data_nascimento:
    wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtData"))).send_keys(data_nascimento)
    time.sleep(3)
    driver.save_screenshot("print3.png")
    wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_btnValidar"))).click()
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ModalButton"))).click()
time.sleep(3)
driver.save_screenshot("print4.png")
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".item:nth-child(1) > label"))).click()
time.sleep(3)
driver.save_screenshot("print5.png")
wait.until(EC.element_to_be_clickable((By.ID, "LinkSegundaVia"))).click()
tipo_emissao = wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_cbTipoEmissao")))
tipo_emissao.click()
wait.until(EC.element_to_be_clickable((By.XPATH, "//option[. = 'Emitir fatura completa']"))).click()
motivo = wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_cbMotivo")))
time.sleep(3)
motivo.click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//option[. = 'Não recebeu a fatura']"))).click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_btEnviar"))).click()
time.sleep(3)

# mes_ano já vem no formato esperado na tabela (ex: "AGO/2025")
pdf_disponivel = False  # Inicializar como False por padrão
pdf_info = None  # Inicializar pdf_info também

try:
    periodo_procurado = mes_ano
    print(f"Procurando período: {periodo_procurado}")
    
    # Aguardar a tabela carregar
    time.sleep(3)
    
    # Procurar pela linha que contém o mês/ano desejado
    xpath_periodo = f"//td[contains(text(), '{periodo_procurado}')]"
    
    try:
        # Verificar se o período existe na tabela
        periodo_cell = wait.until(EC.presence_of_element_located((By.XPATH, xpath_periodo)))
        print(f"Período {periodo_procurado} encontrado na tabela")
        
        # DEBUG: Tirar screenshot da tabela
        driver.save_screenshot(f"tabela_encontrada_{periodo_procurado.replace('/', '_')}.png")
        
        # DEBUG: Mostrar estrutura da linha
        try:
            linha_periodo = periodo_cell.find_element(By.XPATH, "./..")
            print(f"HTML da linha: {linha_periodo.get_attribute('innerHTML')[:300]}...")
            
            # DEBUG: Listar todos os links na linha
            all_links = linha_periodo.find_elements(By.TAG_NAME, "a")
            print(f"Links encontrados na linha ({len(all_links)}):")
            for i, link in enumerate(all_links):
                onclick = link.get_attribute('onclick') or 'sem onclick'
                texto = link.text or 'sem texto'
                print(f"  Link {i+1}: texto='{texto}', onclick='{onclick[:50]}...'")
        except Exception as debug_error:
            print(f"Erro no debug da linha: {debug_error}")
        
        # Encontrar e clicar no botão Download da linha
        try:
            linha_periodo = periodo_cell.find_element(By.XPATH, "./..")  # Pega a linha (tr) pai
            # Procurar por link com onclick contendo 'mostraFaturaCompleta' ou texto 'Download'
            download_link = linha_periodo.find_element(By.XPATH, ".//a[contains(@onclick, 'mostraFaturaCompleta') or contains(text(), 'Download')]")
            print("Clicando no link de download...")
            download_link.click()
            
            time.sleep(3)
            print("Clicando no botão Modal...")
            wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_btnModal"))).click()
            
            print("Aguardando download ser concluído...")
            time.sleep(8)  # Espera para download
            
            pdf_disponivel = True
        except Exception as e:
            print(f"Erro ao clicar no download: {e}")
            pdf_disponivel = False
            time.sleep(3)
            print("Clicando no botão Modal...")
            wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_btnModal"))).click()
            
            print("Aguardando download ser concluído...")
            time.sleep(8)  # Espera mais longa para download
            
            pdf_disponivel = True
        else:
            print("Nenhum método conseguiu clicar no botão Download")
            pdf_disponivel = False
        
    except Exception as e:
        print(f"Período {periodo_procurado} não encontrado na tabela: {e}")
        pdf_disponivel = False
        
except Exception as e:
    print(f"Erro ao processar período {mes_ano}: {e}")
    pdf_disponivel = False


# Processar o arquivo baixado
downloads_path = "/tmp/downloads"  # Mesma pasta configurada no Firefox
pdf_info = None

# Verificar se o PDF está disponível antes de tentar processar
if not pdf_disponivel:
    print(f"PDF para o período {mes_ano} não está disponível")
    pdf_info = {
        'status': 'PDF não disponível',
        'periodo_solicitado': mes_ano,
        'disponivel': False
    }
else:
    print("PDF disponível, processando download...")

try:
    if pdf_disponivel:  # Só tentar baixar se o PDF estiver disponível
        latest_pdf = None
        pdf_files = [f for f in os.listdir(downloads_path) if f.endswith('.pdf')]
        if pdf_files:
            path_latest = max(pdf_files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
            latest_pdf = path_latest
            print(f"PDF encontrado em {downloads_path}: {latest_pdf}")
        else:
            print(f"Nenhum PDF encontrado em {downloads_path}. Arquivos presentes: {os.listdir(downloads_path)}")
    else:
        latest_pdf = None  # Não há PDF para processar

    if latest_pdf:  # Só processar se encontrou um PDF
        nome_limpo = nome.replace(" ", "").replace(".", "").replace("/", "").replace("-", "") if nome else "SemNome"
        unique_filename = f"{mes_ano.replace('/', '-')}-{uc}-{nome_limpo}-EnergiaSolar.pdf"
        
        # Ler PDF e converter para base64 (melhor para API/Bubble)
        import base64
        source_path = os.path.join(downloads_path, latest_pdf)
        
        with open(source_path, 'rb') as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        pdf_info = {
            'filename': unique_filename,
            'original_name': latest_pdf,
            'base64_data': pdf_base64,
            'size': os.path.getsize(source_path),
            'mime_type': 'application/pdf',
            'uc': uc,
            'mes_ano': mes_ano,
            'nome': nome,
            'download_time': str(int(time.time()))
        }
        
        print(f"PDF processado com sucesso: {unique_filename}")
        
        # Apagar o arquivo original da pasta temporária
        try:
            os.remove(source_path)
            print(f"Arquivo temporário removido: {source_path}")
        except Exception as delete_error:
            print(f"Erro ao remover arquivo temporário: {delete_error}")
    else:
        print("Nenhum PDF foi encontrado para processar")

        
except Exception as e:
    print(f"Erro ao processar downloads: {e}")

driver.quit()

# Retornar informações do PDF para o Flask
if pdf_info:
    if pdf_info.get('disponivel') == False:
        print(f"AVISO: PDF não disponível para o período {mes_ano}")
    else:
        print(f"SUCESSO: PDF baixado - {pdf_info['filename']}")
else:
    print("FALHA: Nenhum PDF foi baixado")