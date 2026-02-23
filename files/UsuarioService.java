// Exemplo de código Java com violações LGPD
// Este arquivo é usado para demonstrar o LGPD Guard

package com.exemplo.usuario;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/usuarios")
public class UsuarioService {

    private static final Logger log = LoggerFactory.getLogger(UsuarioService.class);

    // ❌ VIOLAÇÃO Art. 46: CPF em log sem mascaramento
    public void criarUsuario(Usuario usuario) {
        log.info("Criando usuário com CPF: " + usuario.getCpf());

        // ❌ VIOLAÇÃO Art. 46: senha em texto puro
        String senha = usuario.getSenha();
        database.save("INSERT INTO usuarios (cpf, senha) VALUES (?, ?)",
                      usuario.getCpf(), senha);

        // ❌ VIOLAÇÃO Art. 6 (finalidade): CPF enviado para analytics
        analyticsClient.track("user_created", Map.of(
            "cpf", usuario.getCpf(),
            "email", usuario.getEmail()
        ));
    }

    // ❌ VIOLAÇÃO Art. 46: comunicação sem HTTPS
    public void sincronizarDados(Usuario usuario) {
        String url = "http://servico-externo.com.br/api/dados";
        httpClient.post(url, usuario);
    }

    // ✅ CORRETO: CPF mascarado no log
    public void atualizarUsuarioCorreto(Usuario usuario) {
        String cpfMascarado = "***." + usuario.getCpf().substring(4, 7) + ".***-**";
        log.info("Atualizando usuário CPF: " + cpfMascarado);

        // ✅ CORRETO: senha com hash BCrypt
        String senhaHash = bcryptEncoder.encode(usuario.getSenha());
        database.save("UPDATE usuarios SET senha = ? WHERE id = ?",
                      senhaHash, usuario.getId());
    }
}
