"""Testes do limite de tentativas de login por IP — Incremento 17 (A-02).

Regra crítica de segurança (CLAUDE.md 1.4 / 1.5) — merece teste dedicado da
janela, dos limiares e do isolamento entre IPs.
"""
from datetime import datetime, timedelta

from app.models.tentativa_login import TentativaLogin
from app.services import rate_limit

AGORA = datetime(2026, 8, 27, 10, 0, 0)


def _registrar_falhas(db_session, ip, quantidade, *, base=AGORA, espacamento_segundos=1):
    """Insere `quantidade` falhas para `ip`, terminando pouco antes de `base`."""
    for i in range(quantidade):
        db_session.add(
            TentativaLogin(
                email="alvo@passoca.com",
                ip=ip,
                sucesso=False,
                criado_em=base - timedelta(seconds=(i + 1) * espacamento_segundos),
            )
        )
    db_session.commit()


class TestAvaliarIp:
    def test_sem_tentativas_libera(self, db_session):
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == 0.0

    def test_abaixo_do_limiar_de_atraso_libera(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_ATRASO - 1)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == 0.0

    def test_no_limiar_de_atraso_aplica_meio_segundo(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_ATRASO)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == rate_limit.ATRASO_BASE_SEGUNDOS

    def test_atraso_dobra_a_cada_falha(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_ATRASO + 2)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert r.atraso_segundos == rate_limit.ATRASO_BASE_SEGUNDOS * 4

    def test_atraso_tem_teto(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_BLOQUEIO - 1)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == rate_limit.ATRASO_MAX_SEGUNDOS

    def test_no_limiar_de_bloqueio_bloqueia_com_retry_after(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_BLOQUEIO)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert r.bloqueado
        assert r.retry_after_segundos > 0
        assert r.retry_after_segundos <= rate_limit.JANELA.total_seconds()

    def test_falhas_fora_da_janela_nao_contam(self, db_session):
        antiga = AGORA - rate_limit.JANELA - timedelta(minutes=1)
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_BLOQUEIO, base=antiga)
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == 0.0

    def test_sucessos_nao_contam_como_falha(self, db_session):
        for _ in range(rate_limit.LIMIAR_BLOQUEIO + 5):
            db_session.add(
                TentativaLogin(
                    email="dona@passoca.com", ip="1.2.3.4", sucesso=True, criado_em=AGORA
                )
            )
        db_session.commit()
        r = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == 0.0

    def test_ip_diferente_nao_e_afetado(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_BLOQUEIO)
        r = rate_limit.avaliar_ip(db_session, "9.9.9.9", agora=AGORA)
        assert not r.bloqueado
        assert r.atraso_segundos == 0.0

    def test_retry_after_diminui_conforme_falhas_envelhecem(self, db_session):
        _registrar_falhas(db_session, "1.2.3.4", rate_limit.LIMIAR_BLOQUEIO)
        agora_mais_tarde = AGORA + timedelta(minutes=10)
        r1 = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=AGORA)
        r2 = rate_limit.avaliar_ip(db_session, "1.2.3.4", agora=agora_mais_tarde)
        assert r2.retry_after_segundos < r1.retry_after_segundos


class TestRegistrarTentativa:
    def test_grava_a_tentativa(self, db_session):
        rate_limit.registrar_tentativa(
            db_session, email="dona@passoca.com", ip="1.2.3.4", sucesso=False, agora=AGORA
        )
        assert db_session.query(TentativaLogin).count() == 1

    def test_normaliza_email_para_minusculas(self, db_session):
        rate_limit.registrar_tentativa(
            db_session, email="  DONA@Passoca.COM ", ip="1.2.3.4", sucesso=False, agora=AGORA
        )
        registro = db_session.query(TentativaLogin).one()
        assert registro.email == "dona@passoca.com"

    def test_poda_tentativas_antigas(self, db_session):
        antiga = AGORA - rate_limit.RETENCAO - timedelta(days=1)
        db_session.add(
            TentativaLogin(email="x@x.com", ip="1.2.3.4", sucesso=False, criado_em=antiga)
        )
        db_session.commit()

        rate_limit.registrar_tentativa(
            db_session, email="y@y.com", ip="1.2.3.4", sucesso=False, agora=AGORA
        )

        emails = {t.email for t in db_session.query(TentativaLogin).all()}
        assert emails == {"y@y.com"}
