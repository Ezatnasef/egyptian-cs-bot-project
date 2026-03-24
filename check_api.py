import requests

print('health', requests.get('http://127.0.0.1:8000/api/health').status_code, requests.get('http://127.0.0.1:8000/api/health').json())
res = requests.post('http://127.0.0.1:8000/api/chat', json={'message': 'مرحبا يا جميل', 'session_id': 'test1'})
print('chat', res.status_code, res.json())
