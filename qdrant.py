from qdrant_client import QdrantClient, models
import logging
from datetime import datetime, timedelta

client = QdrantClient(url="http://localhost:6333")
model_name = "sentence-transformers/all-MiniLM-L6-v2"
collection_name = "news_collection"
pricing_collection_name = "prices_collection"

def insert_prices(payload):
    payload = list(reversed(payload))
    docs = [models.Document(text=d["date"].isoformat(), model=model_name) for d in payload]
    if not client.collection_exists(pricing_collection_name):
        client.create_collection(
            pricing_collection_name,
            vectors_config=models.VectorParams(
                size=client.get_embedding_size(model_name), distance=models.Distance.COSINE)
        )
    maxi = 0
    offset = 0
    try:
        while True:
            points = client.scroll(collection_name=pricing_collection_name, offset=offset, limit=100, with_payload=False, with_vectors=False)
            if len(points[0]) == 0:
                break
            maxi=int(max(((point.id) for point in points[0])))
            offset += len(points[0])
    except Exception:
        pass
    new_ids = [maxi + 1 + i for i in range(len(payload))]
    logging.info(f"Added {new_ids} for pricing")
    client.upload_collection(
        collection_name=pricing_collection_name,
        vectors=docs,
        ids=new_ids,
        payload=payload,
    )
    return len(payload)

def get_prices_by_date(date_str):
    if not client.collection_exists(pricing_collection_name):
        return []

    results = []
    offset = 0
    while True:
        scroll_result = client.scroll(
            collection_name=pricing_collection_name,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        if not scroll_result or not scroll_result[0]:
            break

        for point in scroll_result[0]:
            payload = point.payload or {}
            date_iso = payload.get("date")
            if not date_iso:
                continue
            try:
                point_date = datetime.fromisoformat(date_iso).strftime("%d.%m.%y")
            except Exception:
                continue
            if point_date == date_str:
                results.append(point)

        if scroll_result[-1] is None:
            break
        offset = scroll_result[-1]
    return results

def delete_old_price_points():
    cutoff = (datetime.now() - timedelta(days=8)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    date_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="date",
                range=models.DatetimeRange(
                    lt=cutoff
                )
            )
        ]
    )
    client.delete_points(collection_name=pricing_collection_name, filter=date_filter)
    logging.info(f"Deleted points with 'date' before {cutoff} from {pricing_collection_name}")


def insert_documents(payload):
    payload = list(reversed(payload))
    docs = [models.Document(text=d["title"] + "\n" + d["content"], model=model_name) for d in payload]

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name,
            vectors_config=models.VectorParams(
                size=client.get_embedding_size(model_name), distance=models.Distance.COSINE)
        )

    maxi = 0
    offset = 0
    try:
        while True:
            points = client.scroll(collection_name=collection_name, offset=offset, limit=100, with_payload=False, with_vectors=False)
            if len(points[0]) == 0:
                break
            maxi=int(max(((point.id) for point in points[0])))
            offset += len(points[0])
    except Exception:
        pass
    new_ids = [maxi + 1 + i for i in range(len(payload))]
    logging.info(f"Added {new_ids}")
    client.upload_collection(
        collection_name=collection_name,
        vectors=docs,
        ids=new_ids,
        payload=payload,
    )
    return len(payload)

def get_existing_titles():
    if not client.collection_exists(collection_name):
        return set()
    titles = set()
    offset = 0
    while True:
        scroll_result = client.scroll(
            collection_name=collection_name,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        if not scroll_result:
            break
        for point in scroll_result[0]:
            payload = point.payload or {}
            title = payload.get("title")
            if title:
                titles.add(title)
        if scroll_result[-1] is None:
            break
        offset = scroll_result[-1]
    return titles

def get_available_dates():
    if not client.collection_exists(collection_name):
        return set()
    dates = set()
    offset = 0
    while True:
        scroll_result = client.scroll(
            collection_name=collection_name,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        if not scroll_result:
            break
        for point in scroll_result[0]:
            payload = point.payload or {}
            date = datetime.fromisoformat(payload.get("date")).strftime("%d.%m.%y")
            if date and date not in dates:
                dates.add(date)
        if scroll_result[-1] is None:
            break
        offset = scroll_result[-1]
    dates = sorted(dates, key=lambda x: datetime.strptime(x, "%d.%m.%y"))
    return dates

def clear_collection():
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        return True
    return False

def get_documents_by_date(date_str):
    if not client.collection_exists(collection_name):
        return []

    results = []
    offset = 0
    while True:
        scroll_result = client.scroll(
            collection_name=collection_name,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        if not scroll_result or not scroll_result[0]:
            break

        for point in scroll_result[0]:
            payload = point.payload or {}
            date_iso = payload.get("date")
            if not date_iso:
                continue
            try:
                point_date = datetime.fromisoformat(date_iso).strftime("%d.%m.%y")
            except Exception:
                continue
            if point_date == date_str:
                results.append(point)

        if scroll_result[-1] is None:
            break
        offset = scroll_result[-1]
    return results