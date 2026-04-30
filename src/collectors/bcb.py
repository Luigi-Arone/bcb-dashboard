"""
Coleta séries temporais da API pública do Banco Central do Brasil.
Documentação: https://api.bcb.gov.br/
"""
 
import requests
import logging
from datetime import datetime, date
from src.db.connection import get_connection
from datetime import date
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

 
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
 
BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
 
# Séries que vamos coletar — mesmo código do schema.sql
SERIES = {
    "433":   "IPCA",
    "432":   "Selic",
    "1":     "Câmbio USD/BRL",
    "24369": "Desemprego",
}

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session
 
 
def fetch_series(code: str, start_date: str = "01/01/2010") -> list[dict]:
    """
    Busca uma série histórica na API do BCB.
    Args:
        code: código da série (ex: "433" para IPCA)
        start_date: data inicial no formato dd/mm/yyyy
    Returns:
        Lista de dicts com chaves 'data' e 'valor'
    """
    today = date.today().strftime("%d/%m/%Y")
    url = BCB_API_URL.format(code=code)
    params = {
        "dataInicial": start_date,
        "dataFinal": today,
    }
    headers = {"Accept": "application/json"}
    session = get_session()
    response = session.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()
 
def parse_records(code: str, raw_data: list[dict]) -> list[tuple]:
    """
    Converte a resposta da API para tuplas prontas para inserção.
 
    Returns:
        Lista de (series_code, date, value)
    """
    records = []
    for item in raw_data:
        try:
            date_obj = datetime.strptime(item["data"], "%d/%m/%Y").date()
            value = float(item["valor"].replace(",", "."))
            records.append((code, date_obj, value))
        except (ValueError, KeyError) as e:
            logger.warning(f"Registro inválido ignorado: {item} — {e}")
    return records
 
 
def upsert_records(records: list[tuple]) -> int:
    """
    Insere registros no banco. Ignora duplicatas (ON CONFLICT DO NOTHING).
 
    Returns:
        Número de linhas inseridas
    """
    if not records:
        return 0
 
    sql = """
        INSERT INTO economic_data (series_code, date, value)
        VALUES (%s, %s, %s)
        ON CONFLICT (series_code, date) DO NOTHING
    """
 
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
            inserted = cur.rowcount
        conn.commit()
 
    return inserted
 
 
def collect_all(start_date: str = None):
    """Coleta todas as séries configuradas e salva no banco."""
    if start_date is None:
        start_date = (date.today() - relativedelta(years=10)).strftime("%d/%m/%Y")
    for code, name in SERIES.items():
        logger.info(f"Coletando: {name} (série {code})")
        try:
            raw = fetch_series(code, start_date)
            records = parse_records(code, raw)
            inserted = upsert_records(records)
            logger.info(f"  ✅ {len(records)} registros processados, {inserted} inseridos")
        except Exception as e:
            logger.error(f"  ❌ Erro ao coletar {name}: {e}")
 
 
if __name__ == "__main__":
    collect_all()