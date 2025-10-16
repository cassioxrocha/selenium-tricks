from flask import Flask, request, jsonify, send_file
from flask_executor import Executor
import time
import uuid
import os
import io
import sys
import contextlib
import base64
import logging
from datetime import datetime

# Configurar logging para arquivo
log_dir = "/tmp/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "selenium_api.log")

# Configurar logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

futures = {}
app = Flask(__name__)
# Configurar executor com múltiplos workers (limitado pelo Selenium)
app.config['EXECUTOR_MAX_WORKERS'] = 2  # Máximo 2 sessões simultâneas
executor = Executor(app)
current_Path = os.path.abspath(os.getcwd())

logger.info(f"Flask API iniciada. Logs sendo gravados em: {log_file}")


class LogCapture:
    """Classe para capturar prints e enviá-los para o logger"""
    def __init__(self, logger):
        self.logger = logger
        self.buffer = io.StringIO()
    
    def write(self, msg):
        if msg.strip():  # Só loga se não for linha vazia
            self.logger.info(f"[SCRIPT] {msg.strip()}")
        self.buffer.write(msg)
    
    def flush(self):
        pass
    
    def getvalue(self):
        return self.buffer.getvalue()

def execute_and_capture(fileName, **kwargs):
    logger.info(f"=== INICIANDO EXECUÇÃO: {fileName} ===")
    logger.info(f"Parâmetros: {kwargs}")
    
    with open(os.path.join(current_Path,fileName), 'r') as file:
        code = file.read()

    # Usar nossa classe personalizada para capturar output
    log_capture = LogCapture(logger)
    
    # Criando um namespace com os parâmetros disponíveis para o script
    namespace = {
        '__name__': '__main__',
        '__file__': os.path.join(current_Path, fileName),
        **kwargs  # Adiciona todos os parâmetros passados
    }
    
    try:
        # Redirecionar stdout e stderr para nossa classe de captura
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        logger.info(f"Executando script {fileName}...")
        exec(code, namespace)
        logger.info(f"Script {fileName} executado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao executar {fileName}: {e}")
        raise
    finally:
        # Restaurar stdout e stderr originais
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    # Capturar informações do PDF se existir no namespace
    pdf_info = namespace.get('pdf_info')
    logger.info(f"pdf_info capturado: {pdf_info}")
    
    result = {
        'output': log_capture.getvalue(),
        'success': True
    }
    
    if pdf_info:
        result['pdf_info'] = pdf_info
        filename = pdf_info.get('filename', 'arquivo não identificado')
        result['message'] = f"PDF baixado: {filename}"
    else:
        result['message'] = "Script executado, mas nenhum PDF foi encontrado"
    
    return result

   
@app.route('/busca_fatura_sync', methods=['POST'])
def busca_fatura_sync():
    """Endpoint síncrono otimizado para Bubble - retorna PDF imediatamente"""
    try:
        data = request.json
        uc = data.get('uc')
        mes_ano = data.get('mes_ano')  # Formato: "AGO/2025"
        documento = data.get('documento')
        nome = data.get('nome')
        data_nascimento = data.get('data_nascimento')
        
        # DEBUG: Log da requisição
        logger.info("=== NOVA REQUISIÇÃO SYNC ===")
        logger.info(f"IP: {request.remote_addr}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'N/A')}")
        logger.info(f"Content-Type: {request.headers.get('Content-Type', 'N/A')}")
        logger.info(f"Dados: UC={uc}, mes_ano={mes_ano}, documento={documento}, nome={nome}")
        logger.info(f"Headers completos: {dict(request.headers)}")
        
        # Validação básica
        if not uc or not documento:
            return jsonify({
                'success': False,
                'error': 'UC and documento are required'
            }), 400
        
        # Executar diretamente (síncrono)
        result = execute_and_capture('scrappy2.py', 
                                   uc=uc, mes_ano=mes_ano, documento=documento, 
                                   nome=nome, data_nascimento=data_nascimento)
        
        if result.get('pdf_info'):
            pdf_info = result['pdf_info']
            
            # Verificar se há erro de login
            if pdf_info.get('status') == 'Erro de login':
                return jsonify({
                    'success': False,
                    'message': 'Erro de login detectado',
                    'error': 'LOGIN_ERROR', 
                    'erro_details': pdf_info.get('erro'),
                    'motivo': pdf_info.get('motivo'),
                    'status': pdf_info.get('status')
                }), 400
            
            # Verificar se há erro na validação
            if pdf_info.get('status') == 'Erro na validação':
                return jsonify({
                    'success': False,
                    'message': 'Erro na validação dos dados',
                    'error': 'VALIDATION_ERROR',
                    'erro_details': pdf_info.get('erro'),
                    'motivo': pdf_info.get('motivo'),
                    'status': pdf_info.get('status')
                }), 400
            
            # Verificar se o PDF não está disponível
            if pdf_info.get('disponivel') == False:
                return jsonify({
                    'success': False,
                    'message': 'PDF não disponível para o período solicitado',
                    'error': 'PDF_NOT_AVAILABLE',
                    'periodo_solicitado': pdf_info.get('periodo_solicitado'),
                    'status': pdf_info.get('status')
                }), 404
            
            # Verificar se é um PDF válido (tem filename)
            if pdf_info.get('filename'):
                # PDF foi baixado com sucesso
                return jsonify({
                    'success': True,
                    'message': 'PDF downloaded successfully',
                    'pdf': {
                        'filename': pdf_info.get('filename'),
                        'data': pdf_info.get('base64_data'),
                        'size_bytes': pdf_info.get('size'),
                        'mime_type': pdf_info.get('mime_type'),
                        'uc': pdf_info.get('uc'),
                        'mes_ano': pdf_info.get('mes_ano'),
                        'nome': pdf_info.get('nome'),
                        'timestamp': pdf_info.get('download_time')
                    }
                })
            else:
                # PDF não foi processado corretamente - mostrar saída completa para debug
                print(f"=== PDF PROCESSING FAILED ===")
                print(f"pdf_info keys: {list(pdf_info.keys()) if pdf_info else 'None'}")
                print(f"pdf_info content: {pdf_info}")
                print(f"Script output (last 500 chars): {result.get('output', '')[-500:]}")
                
                return jsonify({
                    'success': False,
                    'error': 'PDF processing failed - no filename',
                    'debug_info': {
                        'pdf_info_keys': list(pdf_info.keys()) if pdf_info else [],
                        'pdf_info': pdf_info,
                        'output_snippet': result.get('output', '')[-500:]
                    }
                }), 500
        else:
            print(f"=== NO PDF_INFO ===")
            print(f"result keys: {list(result.keys()) if result else 'None'}")
            print(f"Script output (last 500 chars): {result.get('output', '')[-500:]}")
            
            return jsonify({
                'success': False,
                'error': 'No PDF info returned from script',
                'debug_info': {
                    'result_keys': list(result.keys()) if result else [],
                    'output_snippet': result.get('output', '')[-500:]
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Erro interno na API: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500

@app.route('/logs')
def view_logs():
    """Endpoint para visualizar os logs"""
    try:
        with open(log_file, 'r') as f:
            logs = f.read()
        return f"<pre>{logs}</pre>", 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Erro ao ler logs: {e}", 500

@app.route('/logs/tail')
def tail_logs():
    """Endpoint para ver as últimas linhas do log"""
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = ''.join(lines[-50:])  # Últimas 50 linhas
        return f"<pre>{last_lines}</pre>", 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Erro ao ler logs: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)