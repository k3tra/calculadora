import asyncio

from app import solver
from app.schemas import SolutionDraft, SolveRequest, Verificacion


def draft(res):
    return SolutionDraft(pasos=[], resultado_latex=res, resultado_sympy=res)


def run(monkeypatch, drafts, verdicts):
    prompts = []

    async def fake_parse_json(**kw):
        prompts.append(kw["content"])
        return drafts[len(prompts) - 1]

    monkeypatch.setattr(solver, "parse_json", fake_parse_json)
    monkeypatch.setattr(solver, "verify", lambda tipo, latex, d: verdicts[d.resultado_sympy])
    req = SolveRequest(latex="x^2", tipo="derivada")
    return asyncio.run(solver.solve(req)), prompts


def test_reintenta_una_vez_y_envia_el_motivo(monkeypatch):
    verdicts = {"mal": Verificacion(estado="no_verificado", detalle="SymPy obtiene 2*x"),
                "bien": Verificacion(estado="verificado", detalle="ok")}
    sol, prompts = run(monkeypatch, [draft("mal"), draft("bien")], verdicts)
    assert len(prompts) == 2
    assert "SymPy obtiene 2*x" in prompts[1] and "'mal'" in prompts[1]
    assert sol.resultado_sympy == "bien" and sol.verificacion.estado == "verificado"


def test_no_reintenta_si_no_verificable(monkeypatch):
    verdicts = {"a": Verificacion(estado="no_verificable", detalle="x")}
    sol, prompts = run(monkeypatch, [draft("a")], verdicts)
    assert len(prompts) == 1 and sol.verificacion.estado == "no_verificable"


def test_agota_reintentos_y_devuelve_no_verificado(monkeypatch):
    mal = Verificacion(estado="no_verificado", detalle="mal")
    sol, prompts = run(monkeypatch, [draft("a"), draft("b"), draft("c")],
                       {"a": mal, "b": mal, "c": mal})
    assert len(prompts) == solver.MAX_RETRIES + 1
    assert sol.verificacion.estado == "no_verificado"
