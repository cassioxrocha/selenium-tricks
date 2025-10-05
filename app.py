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
        result['message'] = f"PDF baixado: {pdf_info['filename']}"
    else:
        result['message'] = "Script executado, mas nenhum PDF foi encontrado"
    
    return result

@app.route('/tasks')
def tasks():
    task_status = {}
    
    for future_id, future in futures.items():
        if future.done():
            try:
                result = future.result()
                task_status[future_id] = {
                    'status': 'completed',
                    'result_preview': str(result)[:200] + '...' if len(str(result)) > 200 else str(result)
                }
            except Exception as e:
                task_status[future_id] = {
                    'status': 'failed',
                    'error': str(e)
                }
        else:
            task_status[future_id] = {
                'status': 'running' if future.running() else 'pending'
            }
    
    return jsonify({
        'total_tasks': len(futures),
        'tasks': task_status
    })
    


@app.route('/task-status/<future_id>', methods=['GET'])
def task_status(future_id):
    future = futures.get(future_id)
    if future is None:
        return jsonify({'success': False, 'error': 'Invalid task ID'}), 404
    
    if future.done():
        try:
            result = future.result()
            
            # Resposta otimizada para Bubble
            response = {
                'success': True,
                'status': 'completed',
                'message': result.get('message', 'Task completed')
            }
            
            # Se tem PDF, incluir os dados
            if 'pdf_info' in result:
                pdf_info = result['pdf_info']
                response.update({
                    'pdf': {
                        'filename': pdf_info['filename'],
                        'data': pdf_info['base64_data'],
                        'size_bytes': pdf_info['size'],
                        'mime_type': pdf_info['mime_type'],
                        'uc': pdf_info['uc'],
                        'ano_mes': pdf_info['ano_mes'],
                        'nome': pdf_info['nome'],
                        'timestamp': pdf_info['download_time']
                    }
                })
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'failed',
                'error': str(e)
            }), 500
    else:
        status = 'running' if future.running() else 'pending'
        return jsonify({
            'success': True,
            'status': status,
            'message': f'Task is {status}'
        })

@app.route('/busca_fatura', methods=['POST'])
def seleniumAsync():
    data = request.json
    uc = data.get('uc')
    ano_mes = data.get('ano_mes')
    documento = data.get('documento')
    nome = data.get('nome')
    data_nascimento = data.get('data_nascimento')
    future_id = str(uuid.uuid4())
    future = executor.submit(execute_and_capture, 'scrappy2.py', 
                           uc=uc, ano_mes=ano_mes, documento=documento, 
                           nome=nome, data_nascimento=data_nascimento)
    futures[future_id] = future

    return jsonify({'status': 'Task started!','future_id': future_id }), 202

@app.route('/busca_fatura_sync', methods=['POST'])
def busca_fatura_sync():
    """Endpoint síncrono otimizado para Bubble - retorna PDF imediatamente"""
    try:
        data = request.json
        uc = data.get('uc')
        ano_mes = data.get('ano_mes') 
        documento = data.get('documento')
        nome = data.get('nome')
        data_nascimento = data.get('data_nascimento')
        
        # Validação básica
        if not uc or not documento:
            return jsonify({
                'success': False,
                'error': 'UC and documento are required'
            }), 400
        
        # Executar diretamente (síncrono)
        result = execute_and_capture('scrappy2.py', 
                                   uc=uc, ano_mes=ano_mes, documento=documento, 
                                   nome=nome, data_nascimento=data_nascimento)
        
        if result.get('pdf_info'):
            pdf_info = result['pdf_info']
            return jsonify({
                'success': True,
                'message': 'PDF downloaded successfully',
                'pdf': {
                    'filename': pdf_info['filename'],
                    'data': pdf_info['base64_data'],
                    'size_bytes': pdf_info['size'],
                    'mime_type': pdf_info['mime_type'],
                    'uc': pdf_info['uc'],
                    'ano_mes': pdf_info['ano_mes'],
                    'nome': pdf_info['nome'],
                    'timestamp': pdf_info['download_time']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to download PDF',
                'details': result.get('output', '')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500

@app.route('/')
def hello():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug=True)