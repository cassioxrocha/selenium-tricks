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
    uc = "12345678"  # valor padrão para teste
if 'ano_mes' not in locals():
    ano_mes = "202410"  # valor padrão para teste
if 'documento' not in locals():
    documento = ""
if 'nome' not in locals():
    nome = ""
if 'data_nascimento' not in locals():
    data_nascimento = ""

print(f"Parâmetros recebidos: UC={uc}, Ano/Mês={ano_mes}, Documento={documento}")

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
print("Clicando no botão Download...")
wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Download"))).click()
time.sleep(3)
print("Clicando no botão Modal...")
wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_btnModal"))).click()

print("Aguardando download ser concluído...")
time.sleep(8)  # Espera mais longa para download

# Verificar se arquivo apareceu durante a espera
for i in range(3):
    time.sleep(2)
    try:
        files = os.listdir(download_dir)
        pdf_files = [f for f in files if f.endswith('.pdf')]
        print(f"Verificação {i+1}: {len(files)} arquivos, {len(pdf_files)} PDFs na pasta {download_dir}")
        if pdf_files:
            print(f"PDFs encontrados: {pdf_files}")
            break
    except:
        print(f"Verificação {i+1}: erro ao acessar pasta")

print(f"Download finalizado. Verificando pasta final...")

# Processar o arquivo baixado
downloads_path = "/tmp/downloads"  # Mesma pasta configurada no Firefox
local_files_path = "/python-docker/files"
pdf_info = None

try:
    print("Arquivos na pasta downloads:", os.listdir(downloads_path))
    
    # DEBUG: Verificar outras pastas onde o arquivo pode ter sido salvo
    possible_paths = [
        "/tmp/downloads",
        "/tmp", 
        "/home/seluser/Downloads",
        "/home/seluser",
        "/downloads",
        "/usr/downloads"
    ]
    
    print("=== DEBUGANDO POSSÍVEIS LOCAIS DE DOWNLOAD ===")
    for path in possible_paths:
        try:
            if os.path.exists(path):
                files = os.listdir(path)
                pdf_files_in_path = [f for f in files if f.endswith('.pdf')]
                print(f"{path}: {len(files)} arquivos total, {len(pdf_files_in_path)} PDFs")
                if pdf_files_in_path:
                    print(f"  PDFs encontrados: {pdf_files_in_path}")
            else:
                print(f"{path}: pasta não existe")
        except Exception as e:
            print(f"{path}: erro ao acessar - {e}")
    
    # Encontrar o PDF mais recente na pasta configurada
    pdf_files = [f for f in os.listdir(downloads_path) if f.endswith('.pdf')]
    if pdf_files:
        latest_pdf = max(pdf_files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
        
        # Criar nome personalizado: ano_mes-uc-nome-EnergiaSolar.pdf
        # Limpar nome (remover caracteres especiais)
        nome_limpo = nome.replace(" ", "").replace(".", "").replace("/", "").replace("-", "") if nome else "SemNome"
        unique_filename = f"{ano_mes}-{uc}-{nome_limpo}-EnergiaSolar.pdf"
        
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
            'ano_mes': ano_mes,
            'nome': nome,
            'download_time': str(int(time.time()))
        }
        
        print(f"PDF salvo como: {unique_filename}")
        print(f"Informações do PDF: {pdf_info}")
    else:
        print("Nenhum PDF encontrado nos downloads")
        
except Exception as e:
    print(f"Erro ao processar downloads: {e}")

driver.quit()

# Retornar informações do PDF para o Flask
if pdf_info:
    print(f"SUCESSO: PDF baixado - {pdf_info['filename']}")
else:
    print("FALHA: Nenhum PDF foi baixado")