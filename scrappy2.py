from multiprocessing.connection import wait
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time

# Verificar se as variáveis existem (foram passadas do app.py)
if 'uc' not in locals():
    uc = "690381529"  # valor padrão para teste
if 'mes_ano' not in locals():
    mes_ano = "SET/2025"  # valor padrão para teste
if 'documento' not in locals():
    documento = "57581067000184"
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

def check_and_handle_alert(driver, action_description=""):
    """Verifica e trata alerts que podem aparecer"""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"ALERT DETECTADO {action_description}: {alert_text}")
        
        # Se é erro de login, aceitar o alert e retornar False
        if "não foi possível realizar o login" in alert_text.lower() or "#002" in alert_text:
            print("Erro de login detectado, aceitando alert...")
            alert.accept()
            return False, alert_text
        else:
            print("Alert genérico, aceitando...")
            alert.accept()
            return True, alert_text
    except:
        # Não há alert
        return True, None

try:
    driver = webdriver.Remote("http://selenium:4444/wd/hub", options=options)
    print("Conexão com Selenium Grid estabelecida com sucesso")
except Exception as e:
    print(f"ERRO: Falha ao conectar com Selenium Grid: {e}")
    exit()

# Inicializar WebDriverWait com timeout maior
wait = WebDriverWait(driver, 20)

try:
    print("Acessando site da Equatorial...")
    driver.get("https://goias.equatorialenergia.com.br/LoginGO.aspx")
    time.sleep(5)
    print(f"Página carregada: {driver.title}")
    print(f"URL atual: {driver.current_url}")
    
    # Verificar se a página carregou corretamente
    if "Equatorial" not in driver.title and "Login" not in driver.title:
        print(f"AVISO: Título da página inesperado: {driver.title}")
    
    driver.save_screenshot("debug_01_pagina_inicial.png")
    print("Screenshot 01 salva com sucesso")
    
except Exception as e:
    print(f"ERRO ao acessar site: {e}")
    try:
        driver.save_screenshot("debug_00_erro_acesso.png")
        print("Screenshot de erro salva")
    except:
        print("Não foi possível salvar screenshot de erro")
    driver.quit()
    exit()

driver.set_window_size(1024, 768)
time.sleep(3)

try:
    print("Procurando campo UC...")
    print("HTML da página (primeiros 1000 caracteres):")
    print(driver.page_source[:1000])
    
    # Tentar diferentes estratégias para encontrar o campo UC
    uc_field = None
    
    # Estratégia 1: Por ID exato
    try:
        uc_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtUC")))
        print("Campo UC encontrado pelo ID exato")
    except TimeoutException:
        print("Campo UC não encontrado pelo ID exato")
    
    # Estratégia 2: Por ID parcial
    if not uc_field:
        try:
            uc_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id*='txtUC']")))
            print("Campo UC encontrado pelo ID parcial")
        except TimeoutException:
            print("Campo UC não encontrado pelo ID parcial")
    
    # Estratégia 3: Por placeholder ou name
    if not uc_field:
        try:
            uc_field = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='UC' i], input[name*='uc' i]")
            print("Campo UC encontrado por placeholder/name")
        except:
            print("Campo UC não encontrado por placeholder/name")
    
    if uc_field:
        print("Preenchendo UC...")
        uc_field.clear()
        uc_field.send_keys(uc)
        time.sleep(5)
        driver.save_screenshot("debug_02_uc_preenchido.png")
        print("UC preenchido com sucesso")
    else:
        print("ERRO: Campo UC não foi encontrado por nenhuma estratégia!")
        driver.save_screenshot("debug_02_uc_nao_encontrado.png")
        # Mostrar todos os inputs disponíveis
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Inputs disponíveis na página ({len(inputs)}):")
        for i, inp in enumerate(inputs[:10]):  # Mostrar apenas os primeiros 10
            inp_id = inp.get_attribute('id') or 'sem id'
            inp_name = inp.get_attribute('name') or 'sem name'
            inp_placeholder = inp.get_attribute('placeholder') or 'sem placeholder'
            inp_type = inp.get_attribute('type') or 'sem type'
            print(f"  Input {i+1}: id='{inp_id}', name='{inp_name}', placeholder='{inp_placeholder}', type='{inp_type}'")
        driver.quit()
        exit()

except Exception as e:
    print(f"ERRO ao procurar campo UC: {e}")
    driver.save_screenshot("debug_02_erro_uc.png")
    driver.quit()
    exit()

try:
    print("Procurando campo Documento...")
    doc_field = None
    
    # Estratégia 1: Por ID exato
    try:
        doc_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtDocumento")))
        print("Campo Documento encontrado pelo ID exato")
    except TimeoutException:
        print("Campo Documento não encontrado pelo ID exato")
    
    # Estratégia 2: Por ID parcial
    if not doc_field:
        try:
            doc_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id*='txtDocumento']")))
            print("Campo Documento encontrado pelo ID parcial")
        except TimeoutException:
            print("Campo Documento não encontrado pelo ID parcial")
    
    if doc_field:
        print("Preenchendo documento...")
        doc_field.clear()
        doc_field.send_keys(documento)
        time.sleep(5)
        driver.save_screenshot("debug_03_documento_preenchido.png")
        print("Documento preenchido com sucesso")
    else:
        print("ERRO: Campo Documento não encontrado!")
        driver.save_screenshot("debug_03_documento_nao_encontrado.png")
        driver.quit()
        exit()

except Exception as e:
    print(f"ERRO ao procurar campo Documento: {e}")
    driver.save_screenshot("debug_03_erro_documento.png")
    driver.quit()
    exit()

try:
    print("Procurando botão continuar...")
    continue_button = None
    
    # Estratégia 1: Por CSS selector original
    try:
        continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button:nth-child(2)")))
        print("Botão continuar encontrado pelo CSS selector original")
    except TimeoutException:
        print("Botão continuar não encontrado pelo CSS selector original")
    
    # Estratégia 2: Por texto do botão
    if not continue_button:
        try:
            continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Continuar' or @value='CONTINUAR'] | //button[contains(text(), 'Continuar') or contains(text(), 'CONTINUAR')]")))
            print("Botão continuar encontrado por texto")
        except TimeoutException:
            print("Botão continuar não encontrado por texto")
    
    # Estratégia 3: Qualquer botão ou input com class button
    if not continue_button:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".button, input[type='button'], input[type='submit'], button")
            if buttons:
                continue_button = buttons[-1]  # Pegar o último botão (geralmente é o continuar)
                print(f"Usando último botão disponível: {continue_button.get_attribute('value') or continue_button.text}")
        except:
            print("Nenhum botão encontrado")
    
    if continue_button:
        print("Clicando no botão continuar...")
        continue_button.click()
        time.sleep(3)
        print("Botão continuar clicado com sucesso")
    else:
        print("ERRO: Botão continuar não encontrado!")
        driver.save_screenshot("debug_04_botao_nao_encontrado.png")
        # Mostrar todos os botões disponíveis
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], .button")
        print(f"Botões disponíveis na página ({len(buttons)}):")
        for i, btn in enumerate(buttons):
            btn_text = btn.text or btn.get_attribute('value') or 'sem texto'
            btn_class = btn.get_attribute('class') or 'sem class'
            print(f"  Botão {i+1}: texto='{btn_text}', class='{btn_class}'")
        driver.quit()
        exit()

except Exception as e:
    print(f"ERRO ao procurar/clicar botão continuar: {e}")
    driver.save_screenshot("debug_04_erro_continuar.png")
    driver.quit()
    exit()

# Verificar se apareceu algum alert após clicar
success, alert_text = check_and_handle_alert(driver, "após clicar continuar")
if not success:
    print(f"ERRO DE LOGIN: {alert_text}")
    driver.save_screenshot("debug_04_erro_login.png")
    driver.quit()
    # Retornar erro específico para o Flask
    pdf_info = {
        'status': 'Erro de login',
        'erro': alert_text,
        'disponivel': False,
        'motivo': 'Dados de login incorretos ou sistema indisponível'
    }
    exit()

time.sleep(5)
driver.save_screenshot("debug_04_apos_continuar.png")
print(f"URL após continuar: {driver.current_url}")
print(f"Título após continuar: {driver.title}")
if data_nascimento:
    print("Preenchendo data de nascimento...")
    data_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtData")))
    data_field.clear()
    data_field.send_keys(data_nascimento)
    time.sleep(5)
    driver.save_screenshot("debug_05_data_nascimento.png")
    
    print("Clicando em validar...")
    validar_button = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_btnValidar")))
    validar_button.click()
    time.sleep(3)
    
    # Verificar alert após validação
    success, alert_text = check_and_handle_alert(driver, "após validar data")
    if not success:
        print(f"ERRO NA VALIDAÇÃO: {alert_text}")
        driver.save_screenshot("debug_06_erro_validacao.png")
        driver.quit()
        pdf_info = {
            'status': 'Erro na validação',
            'erro': alert_text,
            'disponivel': False,
            'motivo': 'Data de nascimento incorreta ou dados inválidos'
        }
        exit()
    
    time.sleep(5)
    driver.save_screenshot("debug_06_apos_validar.png")

print("Procurando botão modal...")
try:
    # Aguardar mais tempo para modal aparecer
    modal_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ModalButton")))
    print("Modal button encontrado, clicando...")
    modal_button.click()
    time.sleep(5)
    driver.save_screenshot("debug_07_apos_modal.png")
    print(f"URL após modal: {driver.current_url}")
except Exception as e:
    print(f"Erro ao encontrar/clicar no modal: {e}")
    driver.save_screenshot("debug_07_erro_modal.png")
    # Tentar alternativas
    try:
        # Procurar por outros seletores possíveis
        alt_button = driver.find_element(By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Continuar')]")
        alt_button.click()
        time.sleep(5)
    except:
        print("Nenhum botão alternativo encontrado")
print("Procurando item para selecionar...")
try:
    item_selector = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".item:nth-child(1) > label")))
    item_selector.click()
    time.sleep(5)
    driver.save_screenshot("debug_08_item_selecionado.png")
except Exception as e:
    print(f"Erro ao selecionar item: {e}")
    driver.save_screenshot("debug_08_erro_item.png")

print("Procurando link Segunda Via...")
try:
    segunda_via_link = wait.until(EC.element_to_be_clickable((By.ID, "LinkSegundaVia")))
    segunda_via_link.click()
    time.sleep(8)  # Wait mais longo
    driver.save_screenshot("debug_09_apos_segunda_via.png")
    print(f"URL após segunda via: {driver.current_url}")
except Exception as e:
    print(f"Erro ao clicar em Segunda Via: {e}")
    driver.save_screenshot("debug_09_erro_segunda_via.png")
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