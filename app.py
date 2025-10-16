from flask import Flask, request, jsonify, send_file
from flask_executor import Executor
import time
import uuid
import os
import io
import contextlib
import base64

futures = {}
app = Flask(__name__)
# Configurar executor com múltiplos workers (limitado pelo Selenium)
app.config['EXECUTOR_MAX_WORKERS'] = 2  # Máximo 2 sessões simultâneas
executor = Executor(app)
current_Path = os.path.abspath(os.getcwd())


def execute_and_capture(fileName, **kwargs):
    with open(os.path.join(current_Path,fileName), 'r') as file:
        code = file.read()

    output = io.StringIO()
    # Criando um namespace com os parâmetros disponíveis para o script
    namespace = {
        '__name__': '__main__',
        '__file__': os.path.join(current_Path, fileName),
        **kwargs  # Adiciona todos os parâmetros passados
    }
    
    with contextlib.redirect_stdout(output):
        exec(code, namespace)
    
    # Capturar informações do PDF se existir no namespace
    pdf_info = namespace.get('pdf_info')
    
    result = {
        'output': output.getvalue(),
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
        print(f"=== NOVA REQUISIÇÃO ===")
        print(f"User-Agent: {request.headers.get('User-Agent', 'N/A')}")
        print(f"Content-Type: {request.headers.get('Content-Type', 'N/A')}")
        print(f"Dados: UC={uc}, mes_ano={mes_ano}, documento={documento}, nome={nome}")
        
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
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500




if __name__ == '__main__':
    app.run(debug=True)