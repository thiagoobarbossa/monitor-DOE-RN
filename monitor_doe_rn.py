"""
Monitor DOE/RN - Diário Oficial do Estado do Rio Grande do Norte

Funcionalidades principais:
- Procura novas edições normais e extraordinárias do DOE/RN.
- Baixa PDFs novos.
- Extrai texto dos PDFs.
- Procura termos definidos em termos.txt.
- Envia alerta por Telegram quando há edição nova e/ou termos encontrados.
- Emite alerta sonoro no Windows quando encontra termo monitorado.
- Mantém histórico local para não repetir avisos.

Autor: gerado com apoio do ChatGPT para uso pessoal/educacional.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    import winsound  # Disponível no Windows
except ImportError:  # Linux/macOS
    winsound = None


PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
STATE_FILE_DEFAULT = PROJECT_DIR / "estado.json"
TERMS_FILE_DEFAULT = PROJECT_DIR / "termos.txt"
DOWNLOADS_DIR_DEFAULT = PROJECT_DIR / "downloads"
LOGS_DIR_DEFAULT = PROJECT_DIR / "logs"

DOE_HOME_URL = "https://www.diariooficial.rn.gov.br/dei/dorn3/"
DOE_PDF_BASE_URL = "https://webdisk.diariooficial.rn.gov.br/Jornal/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 MonitorDOE-RN/1.0"
)


@dataclass
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    termos_arquivo: Path
    estado_arquivo: Path
    downloads_dir: Path
    logs_dir: Path
    intervalo_minutos: int
    intervalo_variacao_segundos: int
    dias_retroativos: int
    dias_futuros: int
    timeout_requisicao: int
    avisar_nova_edicao: bool
    avisar_sem_termos: bool
    enviar_heartbeat: bool
    heartbeat_horas: int
    baixar_pdfs: bool
    tocar_som: bool
    reprocessar_ja_lidos: bool
    limite_trechos_por_termo: int


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "sim", "s", "yes", "y", "on"}


def load_config() -> Config:
    load_dotenv(ENV_FILE)
    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        termos_arquivo=Path(os.getenv("TERMOS_ARQUIVO", str(TERMS_FILE_DEFAULT))).expanduser(),
        estado_arquivo=Path(os.getenv("ESTADO_ARQUIVO", str(STATE_FILE_DEFAULT))).expanduser(),
        downloads_dir=Path(os.getenv("DOWNLOADS_DIR", str(DOWNLOADS_DIR_DEFAULT))).expanduser(),
        logs_dir=Path(os.getenv("LOGS_DIR", str(LOGS_DIR_DEFAULT))).expanduser(),
        intervalo_minutos=max(1, int(os.getenv("INTERVALO_MINUTOS", "15"))),
        intervalo_variacao_segundos=max(0, int(os.getenv("INTERVALO_VARIACAO_SEGUNDOS", "60"))),
        dias_retroativos=max(0, int(os.getenv("DIAS_RETROATIVOS", "10"))),
        dias_futuros=max(0, int(os.getenv("DIAS_FUTUROS", "1"))),
        timeout_requisicao=max(10, int(os.getenv("TIMEOUT_REQUISICAO", "40"))),
        avisar_nova_edicao=parse_bool(os.getenv("AVISAR_NOVA_EDICAO"), True),
        avisar_sem_termos=parse_bool(os.getenv("AVISAR_SEM_TERMOS"), False),
        enviar_heartbeat=parse_bool(os.getenv("ENVIAR_HEARTBEAT"), True),
        heartbeat_horas=max(1, int(os.getenv("HEARTBEAT_HORAS", "6"))),
        baixar_pdfs=parse_bool(os.getenv("BAIXAR_PDFS"), True),
        tocar_som=parse_bool(os.getenv("TOCAR_SOM"), True),
        reprocessar_ja_lidos=parse_bool(os.getenv("REPROCESSAR_JA_LIDOS"), False),
        limite_trechos_por_termo=max(1, int(os.getenv("LIMITE_TRECHOS_POR_TERMO", "3"))),
    )


def setup_logging(config: Config) -> None:
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = config.logs_dir / "monitor_doe_rn.log"

    # Evita problemas com acentuação no Windows antigo.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
    )
    return session


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"pdfs_processados": {}, "ultima_execucao": None, "ultimo_heartbeat": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("pdfs_processados", {})
        state.setdefault("ultima_execucao", None)
        state.setdefault("ultimo_heartbeat", None)
        return state
    except Exception as exc:
        backup = path.with_suffix(".json.bak")
        logging.warning("Não consegui ler estado.json. Vou criar um novo. Backup: %s. Erro: %s", backup, exc)
        try:
            path.replace(backup)
        except Exception:
            pass
        return {"pdfs_processados": {}, "ultima_execucao": None, "ultimo_heartbeat": None}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_terms(path: Path) -> list[str]:
    if not path.exists():
        exemplo = (
            "# Coloque um termo por linha. Linhas iniciadas com # são ignoradas.\n"
            "SEEC\n"
            "1ª DIREC\n"
            "Professor de História\n"
            "convocação\n"
            "nomeação\n"
        )
        path.write_text(exemplo, encoding="utf-8")
        logging.warning("Arquivo de termos não existia. Criei um exemplo em: %s", path)

    terms: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            term = line.strip()
            if not term or term.startswith("#"):
                continue
            terms.append(term)

    # Remove duplicados preservando ordem.
    seen: set[str] = set()
    unique_terms: list[str] = []
    for term in terms:
        key = normalize_text(term)
        if key not in seen:
            unique_terms.append(term)
            seen.add(key)
    return unique_terms


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_message(text: str, max_len: int = 3900) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) + 1 <= max_len:
            current += ("\n" if current else "") + paragraph
        else:
            if current:
                chunks.append(current)
            current = paragraph[:max_len]
    if current:
        chunks.append(current)
    return chunks


def enviar_telegram(config: Config, mensagem: str) -> bool:
    if not config.telegram_bot_token or not config.telegram_chat_id:
        logging.info("Telegram não configurado. Mensagem que seria enviada:\n%s", mensagem)
        return False

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    ok = True
    for chunk in chunk_message(mensagem):
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": chunk,
            "disable_web_page_preview": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code >= 400:
                ok = False
                logging.error("Erro Telegram %s: %s", resp.status_code, resp.text[:300])
        except Exception as exc:
            ok = False
            logging.error("Erro ao enviar Telegram: %s", exc)
    return ok


def alerta_sonoro(config: Config) -> None:
    if not config.tocar_som:
        return
    try:
        if winsound:
            for _ in range(3):
                winsound.Beep(1800, 450)
                time.sleep(0.15)
        else:
            print("\a\a\a")
    except Exception as exc:
        logging.warning("Não consegui tocar alerta sonoro: %s", exc)


def discover_pdfs_from_home(session: requests.Session, config: Config) -> list[dict[str, str]]:
    """Lê a página oficial e captura links diretos para PDFs."""
    found: dict[str, dict[str, str]] = {}
    try:
        resp = session.get(DOE_HOME_URL, timeout=config.timeout_requisicao)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a.get("href", "")).strip()
            text = " ".join(a.get_text(" ", strip=True).split())
            if ".pdf" not in href.lower():
                continue
            url = urljoin(DOE_HOME_URL, href)
            if "diariooficial.rn.gov.br" not in url:
                continue
            found[url] = {"url": url, "origem": "pagina_oficial", "titulo": text or url}
    except Exception as exc:
        logging.warning("Não consegui ler a página principal do DOE/RN: %s", exc)

    return list(found.values())


def candidate_dates(config: Config) -> Iterable[date]:
    today = date.today()
    start = today - timedelta(days=config.dias_retroativos)
    end = today + timedelta(days=config.dias_futuros)
    days = (end - start).days
    for i in range(days + 1):
        yield start + timedelta(days=i)


def extract_date_from_pdf_item(item: dict[str, str]) -> date | None:
    """Extrai a data do PDF a partir da URL ou do título.

    O DOE/RN costuma usar nomes como:
    - 12026-07-09.pdf
    - 12026-07-09E.pdf

    Esta função procura o padrão AAAA-MM-DD na URL e no título.
    """
    text = f"{item.get('url', '')} {item.get('titulo', '')}"
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_br(value: date | None) -> str:
    """Formata uma data no padrão brasileiro ou informa quando não foi identificada."""
    if value is None:
        return "data não identificada"
    return value.strftime("%d/%m/%Y")


def publication_date_iso(value: date | None) -> str | None:
    """Retorna a data em ISO para salvar no estado.json."""
    return value.isoformat() if value else None


def is_pdf_inside_configured_window(item: dict[str, str], config: Config) -> bool:
    """Retorna True somente se o PDF estiver no período configurado.

    Isso evita que links antigos encontrados na página oficial sejam processados
    quando você quer monitorar apenas hoje e poucos dias anteriores.
    """
    pdf_date = extract_date_from_pdf_item(item)
    if pdf_date is None:
        logging.info("Ignorando PDF sem data identificável: %s", item.get("url"))
        return False

    today = date.today()
    start = today - timedelta(days=config.dias_retroativos)
    end = today + timedelta(days=config.dias_futuros)
    return start <= pdf_date <= end


def build_candidate_pdf_urls(config: Config) -> list[dict[str, str]]:
    """Gera URLs prováveis. Ex.: 12026-07-03.pdf e 12026-07-03E.pdf."""
    candidates: list[dict[str, str]] = []
    for d in candidate_dates(config):
        ds = d.strftime("%Y-%m-%d")
        # O DOE/RN tem usado o prefixo '1' antes da data no webdisk.
        names = [f"1{ds}.pdf", f"1{ds}E.pdf"]
        for name in names:
            candidates.append(
                {
                    "url": urljoin(DOE_PDF_BASE_URL, name),
                    "origem": "padrao_por_data",
                    "titulo": f"DOE/RN {ds}{' - extra' if name.endswith('E.pdf') else ''}",
                }
            )
    return candidates


def pdf_url_exists(session: requests.Session, url: str, config: Config) -> bool:
    """Confere se uma URL candidata realmente existe sem baixar tudo."""
    try:
        head = session.head(url, allow_redirects=True, timeout=config.timeout_requisicao)
        ctype = head.headers.get("content-type", "").lower()
        if head.status_code == 200 and ("pdf" in ctype or url.lower().endswith(".pdf")):
            return True
        if head.status_code in {404, 403, 410}:
            return False
    except Exception:
        pass

    try:
        resp = session.get(
            url,
            headers={"Range": "bytes=0-2048"},
            stream=True,
            timeout=config.timeout_requisicao,
        )
        ctype = resp.headers.get("content-type", "").lower()
        status_ok = resp.status_code in {200, 206}
        content_start = b""
        try:
            content_start = next(resp.iter_content(chunk_size=16), b"")
        except StopIteration:
            content_start = b""
        finally:
            resp.close()
        return status_ok and ("pdf" in ctype or content_start.startswith(b"%PDF"))
    except Exception:
        return False


def discover_all_pdfs(session: requests.Session, config: Config) -> list[dict[str, str]]:
    """Combina links da página oficial com URLs prováveis por data."""
    discovered: dict[str, dict[str, str]] = {}

    for item in discover_pdfs_from_home(session, config):
        discovered[item["url"]] = item

    candidates = build_candidate_pdf_urls(config)
    logging.info("Verificando %d URLs candidatas por data...", len(candidates))
    for item in candidates:
        url = item["url"]
        if url in discovered:
            continue
        if pdf_url_exists(session, url, config):
            discovered[url] = item

    filtered = [
        item
        for item in discovered.values()
        if is_pdf_inside_configured_window(item, config)
    ]

    ignored = len(discovered) - len(filtered)
    if ignored:
        logging.info(
            "Ignorando %d PDF(s) fora da janela configurada: hoje e %d dia(s) para trás.",
            ignored,
            config.dias_retroativos,
        )

    ordered = sorted(filtered, key=lambda x: x["url"])
    return ordered


def safe_filename_from_url(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name or "diario.pdf"


def download_pdf(session: requests.Session, url: str, config: Config) -> bytes:
    resp = session.get(url, timeout=config.timeout_requisicao)
    resp.raise_for_status()
    content = resp.content
    ctype = resp.headers.get("content-type", "").lower()
    if not content.startswith(b"%PDF") and "pdf" not in ctype:
        raise ValueError(f"A resposta não parece ser PDF. Content-Type: {ctype!r}")
    return content


def save_pdf_if_enabled(pdf_bytes: bytes, url: str, config: Config) -> Path | None:
    if not config.baixar_pdfs:
        return None
    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    path = config.downloads_dir / safe_filename_from_url(url)
    if not path.exists():
        path.write_bytes(pdf_bytes)
    return path


def extract_pages_text(pdf_bytes: bytes) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for index, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text") or ""
            except Exception:
                text = ""
            pages.append((index, text))
    return pages


def make_snippet(normalized_page_text: str, normalized_term: str, radius: int = 180) -> str:
    idx = normalized_page_text.find(normalized_term)
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(normalized_page_text), idx + len(normalized_term) + radius)
    snippet = normalized_page_text[start:end]
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(normalized_page_text):
        snippet = snippet + "..."
    return snippet


def find_terms_in_pages(
    pages: list[tuple[int, str]], terms: list[str], limite_trechos_por_termo: int
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    normalized_terms = [(term, normalize_text(term)) for term in terms]

    occurrences_count: dict[str, int] = {term: 0 for term in terms}

    for page_number, page_text in pages:
        normalized_page = normalize_text(page_text)
        if not normalized_page:
            continue
        for original_term, normalized_term in normalized_terms:
            if not normalized_term:
                continue
            if normalized_term not in normalized_page:
                continue
            if occurrences_count[original_term] >= limite_trechos_por_termo:
                continue
            matches.append(
                {
                    "termo": original_term,
                    "pagina": page_number,
                    "trecho": make_snippet(normalized_page, normalized_term),
                }
            )
            occurrences_count[original_term] += 1

    return matches


def summarize_matches(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "Nenhum termo encontrado."

    lines: list[str] = []
    by_term: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        by_term.setdefault(match["termo"], []).append(match)

    for term, term_matches in by_term.items():
        pages = sorted({m["pagina"] for m in term_matches})
        pages_txt = ", ".join(str(p) for p in pages)
        lines.append(f"- Termo: {term} | página(s): {pages_txt}")
        for m in term_matches[:3]:
            trecho = m.get("trecho") or ""
            if trecho:
                lines.append(f"  Trecho: {trecho}")
    return "\n".join(lines)


def process_pdf(
    session: requests.Session,
    config: Config,
    state: dict[str, Any],
    item: dict[str, str],
    terms: list[str],
) -> None:
    url = item["url"]
    processed = state.setdefault("pdfs_processados", {})

    if url in processed and not config.reprocessar_ja_lidos:
        logging.info("Já processado: %s", url)
        return

    logging.info("Baixando e analisando: %s", url)
    pdf_bytes = download_pdf(session, url, config)
    saved_path = save_pdf_if_enabled(pdf_bytes, url, config)
    pages = extract_pages_text(pdf_bytes)
    all_text_size = sum(len(text) for _, text in pages)

    matches = find_terms_in_pages(pages, terms, config.limite_trechos_por_termo)
    now_iso = datetime.now().isoformat(timespec="seconds")

    data_publicacao = extract_date_from_pdf_item(item)
    termos_unicos_para_estado = sorted({m["termo"] for m in matches})

    processed[url] = {
        "titulo": item.get("titulo", ""),
        "origem": item.get("origem", ""),
        "data_publicacao": publication_date_iso(data_publicacao),
        "data_publicacao_formatada": format_date_br(data_publicacao),
        "processado_em": now_iso,
        "arquivo_salvo": str(saved_path) if saved_path else None,
        "paginas": len(pages),
        "caracteres_extraidos": all_text_size,
        "termos_encontrados": termos_unicos_para_estado,
        "quantidade_ocorrencias": len(matches),
    }
    state["ultima_execucao"] = now_iso
    save_state(config.estado_arquivo, state)

    titulo = item.get("titulo") or safe_filename_from_url(url)
    data_publicacao = extract_date_from_pdf_item(item)
    data_publicacao_txt = format_date_br(data_publicacao)
    termos_unicos = sorted({m["termo"] for m in matches})
    termos_txt = ", ".join(termos_unicos) if termos_unicos else "nenhum"

    if matches:
        alerta_sonoro(config)
        mensagem = (
            "🚨 Termo encontrado no Diário Oficial do RN\n\n"
            f"Edição/PDF: {titulo}\n"
            f"Data de publicação: {data_publicacao_txt}\n"
            f"Termos encontrados neste PDF: {termos_txt}\n"
            f"Páginas analisadas: {len(pages)}\n"
            f"PDF: {url}\n\n"
            f"{summarize_matches(matches)}"
        )
        enviar_telegram(config, mensagem)
        logging.info(
            "PDF analisado: %s | data_publicacao=%s | termos_encontrados=%s",
            url,
            data_publicacao_txt,
            termos_txt,
        )
    else:
        logging.info(
            "PDF analisado: %s | data_publicacao=%s | termos_encontrados=nenhum",
            url,
            data_publicacao_txt,
        )
        if config.avisar_nova_edicao and config.avisar_sem_termos:
            mensagem = (
                "📰 Nova edição do Diário Oficial do RN analisada\n\n"
                f"Edição/PDF: {titulo}\n"
                f"Data de publicação: {data_publicacao_txt}\n"
                f"Termos encontrados neste PDF: {termos_txt}\n"
                f"Páginas analisadas: {len(pages)}\n"
                "Resultado: nenhum termo monitorado encontrado.\n"
                f"PDF: {url}"
            )
            enviar_telegram(config, mensagem)
        elif config.avisar_nova_edicao:
            mensagem = (
                "📰 Nova edição do Diário Oficial do RN encontrada e analisada\n\n"
                f"Edição/PDF: {titulo}\n"
                f"Data de publicação: {data_publicacao_txt}\n"
                f"Termos encontrados neste PDF: {termos_txt}\n"
                f"Páginas analisadas: {len(pages)}\n"
                f"PDF: {url}\n\n"
                "Nenhum termo monitorado foi encontrado."
            )
            enviar_telegram(config, mensagem)


def should_send_heartbeat(state: dict[str, Any], config: Config) -> bool:
    if not config.enviar_heartbeat:
        return False
    last = state.get("ultimo_heartbeat")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True
    return datetime.now() - last_dt >= timedelta(hours=config.heartbeat_horas)


def send_heartbeat_if_needed(config: Config, state: dict[str, Any], total_pdfs: int) -> None:
    if not should_send_heartbeat(state, config):
        return
    now_iso = datetime.now().isoformat(timespec="seconds")
    msg = (
        "✅ Monitor DOE/RN ativo\n\n"
        f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"PDFs já registrados no histórico: {total_pdfs}\n"
        f"Intervalo entre verificações: {config.intervalo_minutos} minuto(s)."
    )
    enviar_telegram(config, msg)
    state["ultimo_heartbeat"] = now_iso
    save_state(config.estado_arquivo, state)


def run_cycle(session: requests.Session, config: Config, state: dict[str, Any]) -> None:
    terms = load_terms(config.termos_arquivo)
    if not terms:
        logging.warning("Nenhum termo configurado em %s. O robô só registrará novas edições.", config.termos_arquivo)

    logging.info("Termos monitorados: %s", ", ".join(terms) if terms else "nenhum")
    items = discover_all_pdfs(session, config)
    logging.info("PDFs encontrados para checagem: %d", len(items))

    if not items:
        logging.warning("Nenhum PDF encontrado neste ciclo.")
        return

    for item in items:
        try:
            process_pdf(session, config, state, item, terms)
        except Exception as exc:
            logging.error("Erro ao processar %s: %s", item.get("url"), exc)

    state["ultima_execucao"] = datetime.now().isoformat(timespec="seconds")
    save_state(config.estado_arquivo, state)
    send_heartbeat_if_needed(config, state, len(state.get("pdfs_processados", {})))


def sleep_until_next_cycle(config: Config) -> None:
    base_seconds = config.intervalo_minutos * 60
    jitter = random.randint(0, config.intervalo_variacao_segundos) if config.intervalo_variacao_segundos else 0
    wait_seconds = base_seconds + jitter
    logging.info("Próxima verificação em aproximadamente %d segundo(s).", wait_seconds)
    time.sleep(wait_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor de publicações do Diário Oficial do RN")
    parser.add_argument("--once", action="store_true", help="Executa apenas um ciclo e encerra.")
    parser.add_argument("--test-telegram", action="store_true", help="Envia uma mensagem de teste para o Telegram e encerra.")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config)

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.estado_arquivo.parent.mkdir(parents=True, exist_ok=True)

    logging.info("Iniciando Monitor DOE/RN")
    logging.info("Página oficial: %s", DOE_HOME_URL)
    logging.info("Pasta do projeto: %s", PROJECT_DIR)

    if args.test_telegram:
        ok = enviar_telegram(
            config,
            "✅ Teste do Monitor DOE/RN: se você recebeu esta mensagem, o Telegram está configurado corretamente.",
        )
        if ok:
            logging.info("Mensagem de teste enviada com sucesso.")
        else:
            logging.warning("Mensagem de teste não enviada. Confira TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env.")
        return

    state = load_state(config.estado_arquivo)
    session = create_session()

    while True:
        try:
            run_cycle(session, config, state)
        except KeyboardInterrupt:
            logging.info("Monitor encerrado pelo usuário.")
            break
        except Exception as exc:
            logging.error("Erro geral no ciclo: %s", exc)

        if args.once:
            logging.info("Execução única concluída.")
            break

        sleep_until_next_cycle(config)


if __name__ == "__main__":
    main()
