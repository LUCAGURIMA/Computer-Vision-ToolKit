# Usseewa
APP Híbrido de Visão e Inspeção local
🎯 BOAS PRÁTICAS PARA SEU PROJETO:
O que NÃO versionar:
venv/ - Ambiente virtual (cada dev cria o seu)

pycache/ - Cache do Python

models/*.pt - Modelos são muito grandes (100MB+)

data/ - Dados gerados pelo sistema

.env - Credenciais e configurações sensíveis

logs/ - Logs são gerados automaticamente

O que versionar:
requirements.txt - Dependências

launcher.py - Código principal

core/ - Lógica do sistema

interfaces/ - Interfaces web/desktop

config/settings.py - Configuração padrão

README.md - Documentação

models/README.md - Instruções para baixar modelos