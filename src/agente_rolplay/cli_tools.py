# python3 cli_tools.py (formerly function_tools.py)

from anthropic import Anthropic
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import models, QdrantClient
from qdrant_client.models import PointStruct
from src.agente_rolplay.system_prompt import prompt_clasificador_saludo_inicial

import json
import os

# import pandas as pd
import pytz
import time

load_dotenv()
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 1024))
N_SIMILARITY = int(os.getenv("N_SIMILARITY", 3))
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")

client = Anthropic(api_key=anthropic_api_key)
openai_client = OpenAI(api_key=openai_api_key)
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

dict_clientes_datos = {}


def anthropic_completion(
    system_prompt,
    messages,
    model_name=MODEL_NAME,
    max_tokens=5192,
    temperature=0.0,
    client=client,
):
    answer = client.messages.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        system=system_prompt,
        temperature=temperature,
    )
    return answer


def create_embeddings(
    text, client=openai_client, model=OPENAI_EMBEDDINGS_MODEL, dim=VECTOR_DIMENSION
):
    response = client.embeddings.create(
        input=text,
        model=model,
        dimensions=dim,
    )
    return {"answer": response.data[0].embedding}


def insert_info_business(
    sections,
    client_qdrant=qdrant_client,
    COLLECTION=QDRANT_COLLECTION_NAME,
    dim=VECTOR_DIMENSION,
):
    collections = client_qdrant.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if COLLECTION not in collection_names:
        client_qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config={"embeddings": {"size": dim, "distance": "Cosine"}},
        )
        print(f"Collection '{COLLECTION}' created successfully.")

    points = []

    for index, section in enumerate(sections):
        vector = create_embeddings(section["texto"])

        point = PointStruct(
            id=index,
            vector={"embeddings": vector["answer"]},
            payload={"nombre": section["nombre"], "texto": section["texto"]},
        )

        points.append(point)

    client_qdrant.upsert(collection_name=COLLECTION, points=points)
    print(f"{len(points)} sections inserted into Qdrant.")


def get_text_by_relevance(
    query, client=qdrant_client, collection=QDRANT_COLLECTION_NAME, n=N_SIMILARITY
):
    """
    Search relevant texts in Qdrant using query_points (new API)
    """
    try:
        # Generate embedding for the query
        embedding = create_embeddings(query)

        # NEW API: query_points instead of search
        search_result = client.query_points(
            collection_name=collection,
            query=embedding["answer"],  # Direct vector, no tuple
            using="embeddings",  # Vector name
            limit=n,
            with_payload=True,
        )

        print(f"Search successful: {len(search_result.points)} results")

        # Process results
        relevant_texts = []
        for scored_point in search_result.points:
            relevant_texts.append(
                {
                    "texto": scored_point.payload.get("texto", ""),
                    "nombre": scored_point.payload.get("nombre", ""),
                    "ruta": scored_point.payload.get("ruta", ""),
                    "file_id": scored_point.payload.get("file_id", ""),
                    "score": scored_point.score,
                }
            )

        return relevant_texts

    except Exception as e:
        print(f"Error in Qdrant search: {e}")
        import traceback

        traceback.print_exc()
        return []


def get_mexico_city_time():
    timestamp = time.time()
    utc_time = datetime.utcfromtimestamp(timestamp)
    mexico_city_timezone = pytz.timezone("America/Mexico_City")
    mexico_city_time = utc_time.astimezone(mexico_city_timezone)
    formatted_time = mexico_city_time.strftime("%A, %Y-%m-%d %H:%M")
    return formatted_time


def agregar_punto_individual(
    texto, nombre, client_qdrant=qdrant_client, COLLECTION=QDRANT_COLLECTION_NAME
):
    try:
        # Get the last ID from the collection
        result = client_qdrant.scroll(
            collection_name=COLLECTION,
            limit=1,
            with_payload=False,
            with_vectors=False,
            order_by="id",
        )

        # If there are points, take the last ID and add 1, otherwise start at 0
        if result[0]:
            last_id = max([point.id for point in result[0]]) if result[0] else -1
            new_id = last_id + 1
        else:
            new_id = 0

        vector = create_embeddings(texto)

        point = PointStruct(
            id=new_id,
            vector={"embeddings": vector["answer"]},
            payload={"nombre": nombre, "texto": texto},
        )

        client_qdrant.upsert(collection_name=COLLECTION, points=[point])

        return {
            "success": True,
            "id": new_id,
            "message": "Information added successfully.",
        }

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def insert_datos_pauta(
    sections,
    client_qdrant=qdrant_client,
    COLLECTION=QDRANT_COLLECTION_NAME,
    dim=VECTOR_DIMENSION,
):
    collections = client_qdrant.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if COLLECTION not in collection_names:
        client_qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config={"embeddings": {"size": dim, "distance": "Cosine"}},
        )
        print(f"Collection '{COLLECTION}' created successfully.")

    points = []
    for index, section in enumerate(sections):
        vector = create_embeddings(section["texto_embeddings"])

        point = PointStruct(
            id=index,
            vector={"embeddings": vector["answer"]},
            payload=section["datos_completos_punto"],
            # payload={
            #     "nombre": section["nombre"],
            #     "texto": section["texto"]
            # }
        )
        points.append(point)

    client_qdrant.upsert(collection_name=COLLECTION, points=points)
    print(f"{len(points)} sections inserted into Qdrant.")


# ======================================
def insertar_documentos_drive_a_qdrant(
    json_path="textos_drive_extraidos.json",
    client_qdrant=qdrant_client,
    COLLECTION=QDRANT_COLLECTION_NAME,
    dim=VECTOR_DIMENSION,
):
    """
    Insert documents extracted from Google Drive into Qdrant

    Args:
        json_path (str): Path to JSON file with extracted texts
        client_qdrant: Qdrant client
        COLLECTION (str): Collection name
        dim (int): Embedding dimension
    """
    collections = client_qdrant.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if COLLECTION not in collection_names:
        client_qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config={"embeddings": {"size": dim, "distance": "Cosine"}},
        )
        print(f"Collection '{COLLECTION}' created successfully.")

    else:
        print(f"Collection '{COLLECTION}' already exists.")

    print(f"Loading documents from: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Total documents to process: {len(documents)}")

    points = []

    for index, doc in enumerate(documents):
        print(f"Processing [{index + 1}/{len(documents)}]: {doc['nombre']}")

        # Prepare text for embeddings (name + text)
        text_for_embedding = f"{doc['nombre']}\n\n{doc['texto']}"

        # Limit to first 8000 characters to not exceed token limits
        truncated_text = text_for_embedding[:8000]

        # Generate embedding
        try:
            vector = create_embeddings(truncated_text)

            # Create point with full payload
            point = PointStruct(
                id=index,
                vector={"embeddings": vector["answer"]},
                payload={
                    "file_id": doc["file_id"],
                    "nombre": doc["nombre"],
                    "ruta": doc["ruta"],
                    "mime_type": doc["mime_type"],
                    "texto": doc["texto"],  # Full text in payload
                    "num_caracteres": doc["num_caracteres"],
                    "num_palabras": doc["num_palabras"],
                },
            )

            points.append(point)
            print(f"  Embedding generated for: {doc['nombre']}")

        except Exception as e:
            print(f"  Error generating embedding for {doc['nombre']}: {e}")
            continue

    # Insert all points into Qdrant
    if points:
        print(f"\nInserting {len(points)} documents into Qdrant...")
        client_qdrant.upsert(collection_name=COLLECTION, points=points)
        print(f"{len(points)} documents inserted successfully into Qdrant.")
    else:
        print("No points to insert.")

    return len(points)


def agregar_documento_a_qdrant(file_id, mime_type, nombre, ruta, ruta_temporal):
    """
    Extract text and add document to Qdrant
    Supports: PDF, Google Docs, DOCX
    """
    try:
        print(f"Extracting text from: {nombre}")
        text = None

        # PDF
        if mime_type == "application/pdf":
            import PyPDF2

            with open(ruta_temporal, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"

        # DOCX
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            from docx import Document

            doc = Document(ruta_temporal)
            text = "\n".join([para.text for para in doc.paragraphs])

        # PPTX
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ):
            from pptx import Presentation

            prs = Presentation(ruta_temporal)
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"

        # XLSX
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            import openpyxl

            wb = openpyxl.load_workbook(ruta_temporal)
            text = ""
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                text += f"\n=== Sheet: {sheet_name} ===\n"
                for row in sheet.iter_rows(values_only=True):
                    text += (
                        " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
                    )

        # Google Doc (export from Drive)
        elif mime_type == "application/vnd.google-apps.document":
            from google_drive import obtener_servicio

            service = obtener_servicio()
            request = service.files().export_media(
                fileId=file_id, mimeType="text/plain"
            )
            from io import BytesIO
            from googleapiclient.http import MediaIoBaseDownload

            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)
            text = fh.read().decode("utf-8")

        # IF NONE OF THESE
        else:
            print(f"Unsupported file type for extraction: {mime_type}")
            return False

        print(f" TEXT: ", text)
        if not text or len(text.strip()) < 10:
            print(f"Text too short or empty")
            return False

        print(f"Text extracted: {len(text)} characters")

        # Generate embedding
        text_for_embedding = f"{nombre}\n\n{text[:8000]}"
        embedding = create_embeddings(text_for_embedding)

        # Create point
        point_id = int(time.time())
        point = PointStruct(
            id=point_id,
            vector={"embeddings": embedding["answer"]},
            payload={
                "file_id": file_id,
                "nombre": nombre,
                "ruta": ruta,
                "mime_type": mime_type,
                "texto": text,
                "num_caracteres": len(text),
                "fecha_subida": datetime.now(
                    pytz.timezone("America/Mexico_City")
                ).isoformat(),
            },
        )

        # Insert into Qdrant
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=[point])
        print(f"Added to Qdrant with ID: {point_id}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    insertar_documentos_drive_a_qdrant()

    # Process to insert spreadsheet data into Qdrant
    # file_path = "datos_pauta.xlsx"
    # datos_embeddear = read_spreadsheets_data_and_generate_dict_embeds(file_path)
    # insert_datos_pauta(datos_embeddear)

    # Process to test getting text by relevance
    # consulta = "dime sobre los clientes de san fer ? "
    # consulta = "dame informacion sobre las minutas que hubo el 16 de octubre del 25   "
    # ans = get_text_by_relevance(consulta)
    # print("ans", ans)
