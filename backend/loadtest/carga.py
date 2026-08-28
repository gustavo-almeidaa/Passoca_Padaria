"""Teste de carga do balcão — Incremento 22 (auditoria A-07).

Simula o uso real do sistema: poucos usuários simultâneos (o cenário do
projeto — uma padaria de bairro) rodando o fluxo de balcão em loop:

    login -> listar pedidos do dia -> consultar um pedido ->
    registrar pedido -> avançar status

Python puro (httpx + asyncio, ambos já disponíveis), sem dependência nova.

Uso (com o servidor no ar e um usuário proprietária/atendente válido):

    cd backend
    python loadtest/carga.py \
        --url http://127.0.0.1:8000 \
        --email dona@passoca.com --senha SUA_SENHA \
        --usuarios 5 --rodadas 40

Imprime p50/p95/p99 e média por operação, mais a contagem de erros.

NÃO é benchmark de produção — mede os endpoints em si. Latência de rede,
do Neon e o "dormir" do plano free do Render entram por cima disso. Ver
docs/desempenho.md.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

import httpx


def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * p
    baixo = int(k)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (k - baixo)


async def _preparar(cliente: httpx.AsyncClient) -> tuple[int, int]:
    """Garante que existe pelo menos um cliente e um produto pra usar."""
    clientes = (await cliente.get("/clientes")).json()
    if clientes:
        cliente_id = clientes[0]["id"]
    else:
        resp = await cliente.post(
            "/clientes", json={"nome": "Carga Teste", "telefone": "43900000000"}
        )
        cliente_id = resp.json()["id"]

    produtos = (await cliente.get("/produtos")).json()
    if produtos:
        produto_id = produtos[0]["id"]
    else:
        resp = await cliente.post(
            "/produtos",
            json={
                "nome": "Pão de Carga",
                "categoria": "pao",
                "unidade": "unidade",
                "preco": "5.00",
            },
        )
        produto_id = resp.json()["id"]
    return cliente_id, produto_id


async def _usuario_virtual(
    base_url: str,
    email: str,
    senha: str,
    rodadas: int,
    amostras: dict[str, list[float]],
    erros: dict[str, int],
) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as cliente:
        await _cronometrar("POST /auth/login", amostras, erros, cliente.post,
                           "/auth/login", json={"email": email, "senha": senha})
        cliente_id, produto_id = await _preparar(cliente)
        hoje = date.today().isoformat()

        for _ in range(rodadas):
            await _cronometrar(
                "GET /pedidos (dia)", amostras, erros, cliente.get,
                f"/pedidos?data_inicio={hoje}",
            )

            entrega = datetime.now() + timedelta(days=3)
            corpo = {
                "cliente_id": cliente_id,
                "data_entrega": entrega.date().isoformat(),
                "hora_entrega": entrega.time().replace(microsecond=0).isoformat(),
                "itens": [{"produto_id": produto_id, "quantidade": 1}],
            }
            pedido = await _cronometrar(
                "POST /pedidos", amostras, erros, cliente.post, "/pedidos", json=corpo
            )
            if pedido is not None and pedido.status_code == 201:
                pid = pedido.json()["id"]
                await _cronometrar(
                    "GET /pedidos/{id}", amostras, erros, cliente.get, f"/pedidos/{pid}"
                )
                await _cronometrar(
                    "POST /pedidos/{id}/avancar", amostras, erros, cliente.post,
                    f"/pedidos/{pid}/avancar",
                )


async def _cronometrar(rotulo, amostras, erros, fn, *args, **kwargs):
    inicio = time.perf_counter()
    try:
        resp = await fn(*args, **kwargs)
    except Exception:
        erros[rotulo] += 1
        return None
    decorrido_ms = (time.perf_counter() - inicio) * 1000
    amostras[rotulo].append(decorrido_ms)
    if resp.status_code >= 400:
        erros[rotulo] += 1
    return resp


async def _rodar(args) -> None:
    amostras: dict[str, list[float]] = defaultdict(list)
    erros: dict[str, int] = defaultdict(int)

    inicio = time.perf_counter()
    await asyncio.gather(
        *(
            _usuario_virtual(args.url, args.email, args.senha, args.rodadas, amostras, erros)
            for _ in range(args.usuarios)
        )
    )
    total_s = time.perf_counter() - inicio

    print(f"\n{args.usuarios} usuários x {args.rodadas} rodadas — {total_s:.1f}s\n")
    print(f"{'operação':<28} {'n':>5} {'média':>9} {'p50':>9} {'p95':>9} {'p99':>9} {'erros':>6}")
    print("-" * 80)
    for rotulo in sorted(amostras):
        v = amostras[rotulo]
        print(
            f"{rotulo:<28} {len(v):>5} "
            f"{statistics.mean(v):>8.0f}m {_percentil(v, 0.50):>8.0f}m "
            f"{_percentil(v, 0.95):>8.0f}m {_percentil(v, 0.99):>8.0f}m "
            f"{erros[rotulo]:>6}"
        )

    p95_geral = _percentil([ms for v in amostras.values() for ms in v], 0.95)
    print("-" * 80)
    print(f"p95 agregado: {p95_geral:.0f}ms  (alvo RNF: < 500ms)")
    total_erros = sum(erros.values())
    if total_erros:
        print(f"\n⚠️  {total_erros} respostas de erro (>=400) — ver acima")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", required=True)
    parser.add_argument("--usuarios", type=int, default=5)
    parser.add_argument("--rodadas", type=int, default=40)
    asyncio.run(_rodar(parser.parse_args()))


if __name__ == "__main__":
    main()
