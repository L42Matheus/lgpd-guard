# Exemplo de código Python com violações LGPD
# Este arquivo é usado para demonstrar o LGPD Guard

import logging
import requests

logger = logging.getLogger(__name__)


class UsuarioService:

    def criar_usuario(self, usuario: dict):
        # ❌ VIOLAÇÃO Art. 46: CPF exposto em log
        logger.info(f"Criando usuário CPF: {usuario['cpf']}")

        # ❌ VIOLAÇÃO Art. 46: senha em texto puro no banco
        self.db.execute(
            "INSERT INTO usuarios (cpf, email, senha) VALUES (?, ?, ?)",
            (usuario['cpf'], usuario['email'], usuario['senha'])
        )

        # ❌ VIOLAÇÃO Art. 6: dado pessoal enviado para analytics sem base legal
        requests.post("https://analytics.exemplo.com/track", json={
            "event": "user_created",
            "cpf": usuario['cpf'],
            "email": usuario['email']
        })

    def buscar_por_cpf(self, cpf: str):
        # ❌ VIOLAÇÃO Art. 46: SQL injection com dado pessoal
        query = f"SELECT * FROM usuarios WHERE cpf = '{cpf}'"
        return self.db.execute(query)

    # ✅ CORRETO: CPF mascarado
    def buscar_por_cpf_correto(self, cpf: str):
        logger.info(f"Buscando usuário CPF: ***.***.{cpf[-6:-2]}-**")
        return self.db.execute(
            "SELECT * FROM usuarios WHERE cpf = ?", (cpf,)
        )

# teste
logger.info(f'CPF do usuario: {usuario["cpf"]}')
