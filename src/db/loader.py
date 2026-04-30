from src.db.connection import get_connection


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