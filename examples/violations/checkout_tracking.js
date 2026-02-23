// Exemplo realista de falhas comuns em produto digital (checkout/e-commerce)
// Objetivo: demonstrar violações LGPD que "passam batido" no dia a dia.

async function enviarEventoCheckout(pedido, usuario) {
  // ❌ VIOLAÇÃO Art. 46: e-mail e CPF em log de aplicação
  console.log(`Checkout iniciado para email=${usuario.email} cpf=${usuario.cpf}`);

  // ❌ VIOLAÇÃO Art. 6 + Art. 7: analytics com dado pessoal sem necessidade clara
  analytics.track("checkout_started", {
    email: usuario.email,
    cpf: usuario.cpf,
    orderTotal: pedido.total,
  });

  // ❌ VIOLAÇÃO Art. 6 + Art. 46: dado pessoal em query string (URL)
  await fetch(
    `https://payments.exemplo.com/process?email=${encodeURIComponent(usuario.email)}&cpf=${usuario.cpf}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orderId: pedido.id, total: pedido.total }),
    }
  );
}

// ✅ EXEMPLO CORRETO: minimização de dados e pseudonimização
async function enviarEventoCheckoutSeguro(pedido, usuario) {
  const cpfMascarado = `***.***.${usuario.cpf.slice(-5, -2)}-**`;
  console.log(`Checkout iniciado para usuário=${usuario.id} cpf=${cpfMascarado}`);

  analytics.track("checkout_started", {
    userId: usuario.id,
    orderTotal: pedido.total,
  });

  await fetch("https://payments.exemplo.com/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orderId: pedido.id, total: pedido.total }),
  });
}
