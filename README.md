<!-- # GuardiumAIDemo-backend
Backend para la demo de IBM Guardium AI de Xelere

<img src="https://github.com/user-attachments/assets/4b6f2393-614a-482b-9478-e14f2866555d" width=750px height=auto>
-->

# GuardiumAIDemo-backend
Backend para la demo de IBM Guardium For AI usada en el webinar de Xelere. Simula un microservicio de ATS (recepción de CVs) y un punto de integración donde se inspeccionan/registran solicitudes de inferencia para detectar *prompt injection* antes de enviarlas al modelo.

<img src="https://github.com/user-attachments/assets/364ee9dd-d3cc-4459-8865-b0ecdfba0885" width=750px height=auto>

## Objetivo
Levantar localmente un backend simple que recibe CVs, simula envío a un LLM y muestra cómo una capa de inspección (simulada) puede:
- detectar inyecciones de prompt en texto,
- bloquear o sanitizar la petición,
- registrar el evento para auditoría/alerta (mismo flujo que se demuestra con Guardium For AI en el webinar).

## Plataformas soportadas

<img src="https://github.com/user-attachments/assets/5a3fd087-9d54-486f-8ed2-e3eafb27418c" width=750px height=auto>

## Requisitos
- Python 3.10+  
- pipenv (recomendado) o `venv` + `pip`  
- (Opcional) ngrok para exponer local al frontend si trabajás en máquinas separadas

## Quickstart (local)
```bash
# clonar
git clone https://github.com/LucioFex/GuardiumAIDemo-backend.git
cd GuardiumAIDemo-backend

# instalar (pipenv) o pip
pipenv install --dev
pipenv shell
# o con venv:
# python -m venv .venv && source .venv/bin/activate
# pip install -r requirements.txt

# configurar variables (copia .env.example -> .env y ajustá)
cp .env.example .env
# EDITAR .env si hace falta

# ejecutar
python app.py
# o, si el proyecto usa flask: FLASK_APP=app.py flask run --host=0.0.0.0
```
