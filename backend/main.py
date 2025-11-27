from backend.app.main import app

# Este arquivo é o ponto de entrada para o Azure App Service.
# A instância 'app' é importada de backend/app/main.py e exposta para o Uvicorn/App Service.
# Exemplo de execução local:
#   python -m uvicorn main:app --reload
