from multiprocessing.connection import wait
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time

# Configurar logger para este script
logger = logging.getLogger(__name__)

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

logger.info(f"Parâmetros recebidos: UC={uc}, Mês/Ano={mes_ano}, Documento={documento}, Nome={nome}, Data de Nascimento={data_nascimento}")

# Detectar se é CPF ou CNPJ
documento_limpo = ''.join(filter(str.isdigit, documento))
eh_cpf = len(documento_limpo) == 11
eh_cnpj = len(documento_limpo) == 14

logger.info(f"Documento: {documento_limpo} ({'CPF' if eh_cpf else 'CNPJ' if eh_cnpj else 'INVÁLIDO'})")
options = Options()
options.add_argument('--ignore-ssl-errors=yes')
options.add_argument('--ignore-certificate-errors')

# Configurar pasta de downloads para uma pasta existente e mapeada
download_dir = "/tmp/downloads"

# Criar pasta com permissões adequadas
os.makedirs(download_dir, exist_ok=True, mode=0o777)

# Verificar e ajustar permissões
try:
    import stat
    os.chmod(download_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 777
    logger.info(f"Permissões ajustadas para: {oct(os.stat(download_dir).st_mode)[-3:]}")
except Exception as perm_error:
    logger.error(f"Erro ao ajustar permissões: {perm_error}")

# DEBUG: Verificar se a pasta foi criada e suas permissões
logger.info(f"Pasta de downloads: {download_dir}")
logger.info(f"Pasta existe: {os.path.exists(download_dir)}")
logger.info(f"Pasta é escrita: {os.access(download_dir, os.W_OK)}")
logger.info(f"Pasta é lida: {os.access(download_dir, os.R_OK)}")

# Limpar pasta antes de usar
try:
    for arquivo in os.listdir(download_dir):
        arquivo_path = os.path.join(download_dir, arquivo)
        if os.path.isfile(arquivo_path):
            os.remove(arquivo_path)
    logger.info("Pasta de downloads limpa")
except Exception as clean_error:
    logger.error(f"Erro ao limpar pasta: {clean_error}")

# Configurações mais robustas do Firefox para download
options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.download.dir", download_dir)
options.set_preference("browser.download.manager.showWhenStarting", False) 
options.set_preference("browser.download.useDownloadDir", True)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/x-pdf,application/octet-stream")
options.set_preference("browser.download.manager.alertOnEXEOpen", False)
options.set_preference("browser.download.manager.focusWhenStarting", False)
options.set_preference("browser.download.manager.useWindow", False)
options.set_preference("browser.download.manager.showAlertOnComplete", False)
options.set_preference("browser.download.manager.closeWhenDone", True)

# Configurações adicionais para melhorar a confiabilidade do download
options.set_preference("browser.download.improvements_to_download_panel", False)
options.set_preference("browser.download.always_ask_before_handling_new_types", False)
options.set_preference("browser.download.panel.shown", False)
options.set_preference("browser.download.start_downloads_in_tmp_dir", False)
options.set_preference("browser.download.alwaysOpenPanel", False)
options.set_preference("security.fileuri.strict_origin_policy", False)
options.set_preference("network.http.phishy-userpass-length", 255)
options.set_preference("network.automatic-ntlm-auth.trusted-uris", "*")

# Configurações de timeout
options.set_preference("network.http.connection-timeout", 60)
options.set_preference("network.http.response.timeout", 60)

# Configurações específicas para resolver problemas de download
options.set_preference("browser.download.forbid_open_with", False)
options.set_preference("browser.download.manager.retention", 0)
options.set_preference("browser.download.skipConfirmLaunchExecutable", True)
options.set_preference("browser.safebrowsing.downloads.enabled", False)
options.set_preference("browser.safebrowsing.downloads.remote.enabled", False)
options.set_preference("security.sandbox.content.level", 0)  # Desabilitar sandbox que pode impedir downloads

# Forçar diretório específico
options.set_preference("browser.download.lastDir", download_dir)
options.set_preference("browser.download.downloadDir", download_dir)

logger.info(f"Firefox configurado para baixar em: {download_dir}")

def check_and_handle_alert(driver, action_description=""):
    """Verifica e trata alerts que podem aparecer"""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        logger.warning(f"ALERT DETECTADO {action_description}: {alert_text}")
        
        # Se é erro de login, aceitar o alert e retornar False
        if "não foi possível realizar o login" in alert_text.lower() or "#002" in alert_text:
            logger.error("Erro de login detectado, aceitando alert...")
            alert.accept()
            return False, alert_text
        else:
            logger.info("Alert genérico, aceitando...")
            alert.accept()
            return True, alert_text
    except:
        # Não há alert
        return True, None

try:
    driver = webdriver.Remote("http://selenium:4444/wd/hub", options=options)
    logger.info("Conexão com Selenium Grid estabelecida com sucesso")
except Exception as e:
    logger.error(f"ERRO: Falha ao conectar com Selenium Grid: {e}")
    exit()

# Inicializar WebDriverWait com timeout maior
wait = WebDriverWait(driver, 20)

try:
    logger.info("Acessando site da Equatorial...")
    driver.get("https://goias.equatorialenergia.com.br/LoginGO.aspx")
    time.sleep(5)
    logger.info(f"Página carregada: {driver.title}")
    logger.info(f"URL atual: {driver.current_url}")
    
    # Verificar se a página carregou corretamente
    if "Equatorial" not in driver.title and "Login" not in driver.title:
        logger.warning(f"AVISO: Título da página inesperado: {driver.title}")
    
    driver.save_screenshot("debug_01_pagina_inicial.png")
    logger.info("Screenshot 01 salva com sucesso")
    
except Exception as e:
    logger.error(f"ERRO ao acessar site: {e}")
    try:
        driver.save_screenshot("debug_00_erro_acesso.png")
        logger.info("Screenshot de erro salva")
    except:
        logger.error("Não foi possível salvar screenshot de erro")
    driver.quit()
    exit()

driver.set_window_size(1024, 768)
time.sleep(3)

try:
    logger.info("Procurando campo UC...")
    logger.debug("HTML da página (primeiros 1000 caracteres):")
    logger.debug(driver.page_source[:1000])
    
    # Tentar diferentes estratégias para encontrar o campo UC
    uc_field = None
    
    # Estratégia 1: Por ID exato
    try:
        uc_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtUC")))
        logger.info("Campo UC encontrado pelo ID exato")
    except TimeoutException:
        logger.debug("Campo UC não encontrado pelo ID exato")
    
    # Estratégia 2: Por ID parcial
    if not uc_field:
        try:
            uc_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id*='txtUC']")))
            logger.info("Campo UC encontrado pelo ID parcial")
        except TimeoutException:
            logger.debug("Campo UC não encontrado pelo ID parcial")
    
    # Estratégia 3: Por placeholder ou name
    if not uc_field:
        try:
            uc_field = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='UC' i], input[name*='uc' i]")
            logger.info("Campo UC encontrado por placeholder/name")
        except:
            logger.debug("Campo UC não encontrado por placeholder/name")
    
    if uc_field:
        logger.info("Preenchendo UC...")
        uc_field.clear()
        uc_field.send_keys(uc)
        time.sleep(5)
        driver.save_screenshot("debug_02_uc_preenchido.png")
        logger.info("UC preenchido com sucesso")
    else:
        logger.error("ERRO: Campo UC não foi encontrado por nenhuma estratégia!")
        driver.save_screenshot("debug_02_uc_nao_encontrado.png")
        # Mostrar todos os inputs disponíveis
        inputs = driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"Inputs disponíveis na página ({len(inputs)}):")
        for i, inp in enumerate(inputs[:10]):  # Mostrar apenas os primeiros 10
            inp_id = inp.get_attribute('id') or 'sem id'
            inp_name = inp.get_attribute('name') or 'sem name'
            inp_placeholder = inp.get_attribute('placeholder') or 'sem placeholder'
            inp_type = inp.get_attribute('type') or 'sem type'
            logger.info(f"  Input {i+1}: id='{inp_id}', name='{inp_name}', placeholder='{inp_placeholder}', type='{inp_type}'")
        driver.quit()
        exit()

except Exception as e:
    logger.error("ERRO ao procurar campo UC: {e}")
    driver.save_screenshot("debug_02_erro_uc.png")
    driver.quit()
    exit()

try:
    logger.info("Procurando campo Documento...")
    doc_field = None
    
    # Estratégia 1: Por ID exato
    try:
        doc_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtDocumento")))
        logger.info("Campo Documento encontrado pelo ID exato")
    except TimeoutException:
        logger.info("Campo Documento não encontrado pelo ID exato")
    
    # Estratégia 2: Por ID parcial
    if not doc_field:
        try:
            doc_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id*='txtDocumento']")))
            logger.info("Campo Documento encontrado pelo ID parcial")
        except TimeoutException:
            logger.info("Campo Documento não encontrado pelo ID parcial")
    
    if doc_field:
        logger.info("Preenchendo documento...")
        doc_field.clear()
        doc_field.send_keys(documento_limpo)
        time.sleep(5)
        driver.save_screenshot("debug_03_documento_preenchido.png")
        logger.info("Documento preenchido com sucesso")
    else:
        logger.error("ERRO: Campo Documento não encontrado!")
        driver.save_screenshot("debug_03_documento_nao_encontrado.png")
        driver.quit()
        exit()

except Exception as e:
    logger.error("ERRO ao procurar campo Documento: {e}")
    driver.save_screenshot("debug_03_erro_documento.png")
    driver.quit()
    exit()

try:
    logger.info("Procurando botão continuar...")
    continue_button = None
    
    # Estratégia 1: Por CSS selector original
    try:
        continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button:nth-child(2)")))
        logger.info("Botão continuar encontrado pelo CSS selector original")
    except TimeoutException:
        logger.info("Botão continuar não encontrado pelo CSS selector original")
    
    # Estratégia 2: Por texto do botão
    if not continue_button:
        try:
            continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Continuar' or @value='CONTINUAR'] | //button[contains(text(), 'Continuar') or contains(text(), 'CONTINUAR')]")))
            logger.info("Botão continuar encontrado por texto")
        except TimeoutException:
            logger.info("Botão continuar não encontrado por texto")
    
    # Estratégia 3: Qualquer botão ou input com class button
    if not continue_button:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".button, input[type='button'], input[type='submit'], button")
            if buttons:
                continue_button = buttons[-1]  # Pegar o último botão (geralmente é o continuar)
                logger.info(f"Usando último botão disponível: {continue_button.get_attribute('value') or continue_button.text}")
        except:
            logger.info("Nenhum botão encontrado")
    
    if continue_button:
        logger.info("Clicando no botão continuar...")
        continue_button.click()
        time.sleep(3)
        logger.info("Botão continuar clicado com sucesso")
        
        # Verificar se apareceu algum alert após clicar
        success, alert_text = check_and_handle_alert(driver, "após clicar continuar")
        if not success:
            logger.error("ERRO DE LOGIN: {alert_text}")
            driver.save_screenshot("debug_04_erro_login.png")
            driver.quit()
            # Retornar erro específico para o Flask
            pdf_info = {
                'status': 'Erro de login',
                'erro': alert_text,
                'disponivel': False,
                'motivo': 'Dados de login incorretos ou sistema indisponível',
                'filename': None
            }
            exit()
    else:
        logger.error("ERRO: Botão continuar não encontrado!")
        driver.save_screenshot("debug_04_botao_nao_encontrado.png")
        # Mostrar todos os botões disponíveis
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], .button")
        logger.info(f"Botões disponíveis na página ({len(buttons)}):")
        for i, btn in enumerate(buttons):
            btn_text = btn.text or btn.get_attribute('value') or 'sem texto'
            btn_class = btn.get_attribute('class') or 'sem class'
            logger.info(f"  Botão {i+1}: texto='{btn_text}', class='{btn_class}'")
        driver.quit()
        exit()

except Exception as e:
    logger.error("ERRO ao procurar/clicar botão continuar: {e}")
    driver.save_screenshot("debug_04_erro_continuar.png")
    driver.quit()
    exit()

# Aguardar e verificar resultado do clique em continuar
time.sleep(5)

# Verificar se há alert ANTES de tentar screenshot
success, alert_text = check_and_handle_alert(driver, "verificação final após continuar")
if not success:
    logger.error("ERRO DE LOGIN FINAL: {alert_text}")
    try:
        driver.save_screenshot("debug_04_erro_login_final.png")
    except:
        logger.info("Não foi possível salvar screenshot do erro")
    driver.quit()
    # Retornar erro específico para o Flask
    pdf_info = {
        'status': 'Erro de login',
        'erro': alert_text,
        'disponivel': False,
        'motivo': 'Dados de login incorretos ou sistema indisponível',
        'filename': None
    }
    exit()

try:
    driver.save_screenshot("debug_04_apos_continuar.png")
    logger.info(f"URL após continuar: {driver.current_url}")
    logger.info(f"Título após continuar: {driver.title}")
except Exception as e:
    logger.error("ERRO ao fazer screenshot/obter info da página: {e}")



# Só preencher data de nascimento se for CPF
if eh_cpf and data_nascimento:
    try:
        logger.info("Documento é CPF - Preenchendo data de nascimento...")
        data_field = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_txtData")))
        data_field.clear()
        data_field.send_keys(data_nascimento)
        time.sleep(5)
        driver.save_screenshot("debug_05_data_nascimento.png")
        
        logger.info("Clicando em validar...")
        validar_button = wait.until(EC.element_to_be_clickable((By.ID, "WEBDOOR_headercorporativogo_btnValidar")))
        validar_button.click()
        time.sleep(3)
        
        # Verificar alert após validação
        success, alert_text = check_and_handle_alert(driver, "após validar data")
        if not success:
            logger.error("ERRO NA VALIDAÇÃO: {alert_text}")
            driver.save_screenshot("debug_06_erro_validacao.png")
            driver.quit()
            pdf_info = {
                'status': 'Erro na validação',
                'erro': alert_text,
                'disponivel': False,
                'motivo': 'Data de nascimento incorreta ou dados inválidos',
                'filename': None
            }
            exit()
        
        time.sleep(5)
        driver.save_screenshot("debug_06_apos_validar.png")
    
    except Exception as e:
        logger.error("ERRO ao preencher data de nascimento: {e}")
        driver.save_screenshot("debug_06_erro_data.png")
        
elif eh_cnpj:
    logger.info("Documento é CNPJ - Pulando preenchimento de data de nascimento")
    driver.save_screenshot("debug_05_cnpj_sem_data.png")
    
else:
    logger.info("Tipo de documento não identificado ou data não fornecida")
    driver.save_screenshot("debug_05_documento_indefinido.png")

logger.info("Procurando botão modal...")
try:
    # Aguardar mais tempo para modal aparecer
    modal_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ModalButton")))
    logger.info("Modal button encontrado, clicando...")
    modal_button.click()
    time.sleep(5)
    driver.save_screenshot("debug_07_apos_modal.png")
    logger.info(f"URL após modal: {driver.current_url}")
except Exception as e:
    logger.error("ERRO ao encontrar/clicar no modal: {e}")
    driver.save_screenshot("debug_07_erro_modal.png")
    # Tentar alternativas
    try:
        # Procurar por outros seletores possíveis
        alt_button = driver.find_element(By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Continuar')]")
        alt_button.click()
        time.sleep(5)
    except:
        logger.info("Nenhum botão alternativo encontrado")
logger.info("Procurando item para selecionar...")
try:
    item_selector = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".item:nth-child(1) > label")))
    item_selector.click()
    time.sleep(5)
    driver.save_screenshot("debug_08_item_selecionado.png")
except Exception as e:
    logger.error("ERRO ao selecionar item: {e}")
    driver.save_screenshot("debug_08_erro_item.png")

logger.info("Procurando link Segunda Via...")
try:
    segunda_via_link = wait.until(EC.element_to_be_clickable((By.ID, "LinkSegundaVia")))
    segunda_via_link.click()
    time.sleep(8)  # Wait mais longo
    driver.save_screenshot("debug_09_apos_segunda_via.png")
    logger.info(f"URL após segunda via: {driver.current_url}")
except Exception as e:
    logger.error("ERRO ao clicar em Segunda Via: {e}")
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
    logger.info(f"Procurando período: {periodo_procurado}")
    
    # Aguardar a tabela carregar
    time.sleep(3)
    
    # Procurar pela linha que contém o mês/ano desejado
    xpath_periodo = f"//td[contains(text(), '{periodo_procurado}')]"
    
    try:
        # Verificar se o período existe na tabela
        periodo_cell = wait.until(EC.presence_of_element_located((By.XPATH, xpath_periodo)))
        logger.info(f"Período {periodo_procurado} encontrado na tabela")
        
        # DEBUG: Tirar screenshot da tabela
        driver.save_screenshot(f"tabela_encontrada_{periodo_procurado.replace('/', '_')}.png")
        
        # DEBUG: Mostrar estrutura da linha
        try:
            linha_periodo = periodo_cell.find_element(By.XPATH, "./..")
            logger.info(f"HTML da linha: {linha_periodo.get_attribute('innerHTML')[:300]}...")
            
            # DEBUG: Listar todos os links na linha
            all_links = linha_periodo.find_elements(By.TAG_NAME, "a")
            logger.info(f"Links encontrados na linha ({len(all_links)}):")
            for i, link in enumerate(all_links):
                onclick = link.get_attribute('onclick') or 'sem onclick'
                texto = link.text or 'sem texto'
                logger.info(f"  Link {i+1}: texto='{texto}', onclick='{onclick[:50]}...'")
        except Exception as debug_error:
            logger.error("ERRO no debug da linha: {debug_error}")
        
        # Encontrar e clicar no botão Download da linha
        linha_periodo = periodo_cell.find_element(By.XPATH, "./..")  # Pega a linha (tr) pai
        
        # Procurar por qualquer link de download na linha
        download_links = linha_periodo.find_elements(By.TAG_NAME, "a")
        download_clicado = False
        
        logger.info(f"=== TENTANDO CLICAR NOS LINKS ===")
        for i, link in enumerate(download_links):
            onclick = link.get_attribute('onclick') or ''
            texto = link.text or ''
            href = link.get_attribute('href') or ''
            
            logger.info(f"Link {i+1}: texto='{texto}', onclick='{onclick[:100]}...', href='{href[:50]}...'")
            
            # Se contém 'Download' no texto ou alguma função de download no onclick
            if 'Download' in texto or 'download' in onclick.lower() or 'mostraFaturaCompleta' in onclick:
                try:
                    logger.info(f"*** TENTANDO BAIXAR PDF: {texto} ***")
                    
                    # Tentar extrair URL do PDF do onclick
                    pdf_url = None
                    if 'mostraFaturaCompleta' in onclick:
                        # Extrair parâmetros do onclick
                        import re
                        match = re.search(r"mostraFaturaCompleta\('([^']+)',\s*'([^']+)',\s*'([^']+)'", onclick)
                        if match:
                            param1, param2, param3 = match.groups()
                            pdf_url = f"https://goias.equatorialenergia.com.br/AgenciaGO/Servicos/aberto/mostrarFaturaCompleta.jsp?param1={param1}&param2={param2}&param3={param3}"
                            logger.info(f"URL do PDF extraída: {pdf_url}")
                    
                    # Se conseguimos extrair a URL, baixar diretamente
                    if pdf_url:
                        try:
                            logger.info("Tentando download direto via requests...")
                            import requests
                            
                            # Usar cookies do navegador
                            cookies = driver.get_cookies()
                            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                            
                            headers = {
                                'User-Agent': driver.execute_script("return navigator.userAgent;"),
                                'Referer': driver.current_url
                            }
                            
                            response = requests.get(pdf_url, cookies=cookie_dict, headers=headers, timeout=30)
                            
                            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                                # Salvar PDF
                                pdf_filename = f"fatura_{periodo_procurado.replace('/', '_')}.pdf"
                                pdf_path = os.path.join(download_dir, pdf_filename)
                                
                                with open(pdf_path, 'wb') as f:
                                    f.write(response.content)
                                
                                logger.info(f"✅ PDF baixado com sucesso: {pdf_path}")
                                pdf_disponivel = True
                                download_clicado = True
                                break
                            else:
                                logger.info(f"❌ Resposta inválida: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
                        
                        except Exception as download_error:
                            logger.info(f"❌ Erro no download direto: {download_error}")
                            # Fallback para método original
                            pass
                    
                    # Se o download direto falhou, tentar método original
                    if not download_clicado:
                        logger.info("Tentando método original (clique + modal)...")
                        # Tentar scroll até o elemento
                        driver.execute_script("arguments[0].scrollIntoView();", link)
                        time.sleep(1)
                    
                    # Tentar clique normal
                    link.click()
                    logger.info(f"✅ Clique normal funcionou")
                    download_clicado = True
                    break
                    
                except Exception as e:
                    logger.info(f"❌ Erro no clique normal: {e}")
                    
                    # Tentar JavaScript click
                    try:
                        driver.execute_script("arguments[0].click();", link)
                        logger.info(f"✅ JavaScript click funcionou")
                        download_clicado = True
                        break
                    except Exception as e2:
                        logger.info(f"❌ Erro no JavaScript click: {e2}")
                        continue
        
        logger.info(f"=== RESULTADO DO CLIQUE: {'SUCESSO' if download_clicado else 'FALHA'} ===")
        
        if download_clicado:
            try:
                time.sleep(3)
                logger.info("Clicando no botão Modal...")
                wait.until(EC.element_to_be_clickable((By.ID, "CONTENT_btnModal"))).click()
                
                logger.info("Aguardando download ser concluído...")
                
                # Aguardar mais tempo e verificar se o download realmente aconteceu
                max_tentativas = 15  # 30 segundos total
                for i in range(max_tentativas):
                    time.sleep(2)
                    
                    # Verificar se há arquivos na pasta de download
                    arquivos = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
                    if arquivos:
                        logger.info(f"✅ PDF encontrado após {(i+1)*2} segundos: {arquivos}")
                        pdf_disponivel = True
                        break
                    
                    logger.info(f"⏳ Tentativa {i+1}/{max_tentativas} - Aguardando download...")
                
                if not pdf_disponivel:
                    logger.info("❌ Timeout: Download não foi concluído após 30 segundos")
                    # Verificar se o download aparece como falha no Firefox
                    try:
                        # Tentar abrir a aba de downloads do Firefox
                        driver.execute_script("window.open('about:downloads', '_blank');")
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(3)
                        driver.save_screenshot("debug_downloads_firefox.png")
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass
                else:
                    logger.info("Download realizado com sucesso!")
                
            except Exception as e:
                logger.error("ERRO ao clicar no botão modal: {e}")
                # Mesmo com erro no modal, o download pode ter acontecido
                time.sleep(8)
                pdf_disponivel = True  # Assumir que deu certo
        else:
            logger.info("Nenhum link de download encontrado na linha")
            pdf_disponivel = False
        
    except Exception as e:
        logger.info(f"Período {periodo_procurado} não encontrado na tabela: {e}")
        pdf_disponivel = False
        
except Exception as e:
    logger.error("ERRO ao processar período {mes_ano}: {e}")
    pdf_disponivel = False


# Processar o arquivo baixado
downloads_path = "/tmp/downloads"  # Mesma pasta configurada no Firefox
pdf_info = None

logger.info(f"=== PROCESSANDO ARQUIVOS BAIXADOS ===")
logger.info(f"pdf_disponivel = {pdf_disponivel}")

# Listar arquivos na pasta antes de processar
try:
    files_before = os.listdir(downloads_path)
    logger.info(f"Arquivos na pasta downloads: {files_before}")
except Exception as e:
    logger.error("ERRO ao listar pasta downloads: {e}")
    files_before = []

# Verificar se o PDF está disponível antes de tentar processar
if not pdf_disponivel:
    logger.info(f"PDF para o período {mes_ano} NÃO está disponível")
    pdf_info = {
        'status': 'PDF não disponível',
        'periodo_solicitado': mes_ano,
        'disponivel': False,
        'filename': None
    }
else:
    logger.info(f"PDF para o período {mes_ano} ESTÁ disponível - processando...")

try:
    if pdf_disponivel:  # Só tentar baixar se o PDF estiver disponível
        latest_pdf = None
        pdf_files = [f for f in os.listdir(downloads_path) if f.endswith('.pdf')]
        if pdf_files:
            path_latest = max(pdf_files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
            latest_pdf = path_latest
            logger.info(f"PDF encontrado em {downloads_path}: {latest_pdf}")
        else:
            logger.info(f"Nenhum PDF encontrado em {downloads_path}. Arquivos presentes: {os.listdir(downloads_path)}")
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
        
        logger.info(f"PDF processado com sucesso: {unique_filename}")
        
        # Apagar o arquivo original da pasta temporária
        try:
            os.remove(source_path)
            logger.info(f"Arquivo temporário removido: {source_path}")
        except Exception as delete_error:
            logger.error("ERRO ao remover arquivo temporário: {delete_error}")
    else:
        logger.info("Nenhum PDF foi encontrado para processar")

        
except Exception as e:
    logger.error("ERRO ao processar downloads: {e}")

driver.quit()

# Retornar informações do PDF para o Flask
if pdf_info:
    if pdf_info.get('disponivel') == False:
        logger.warning("AVISO: PDF não disponível para o período {mes_ano}")
    else:
        logger.info(f"SUCESSO: PDF baixado - {pdf_info['filename']}")
else:
    logger.info("FALHA: Nenhum PDF foi baixado")





