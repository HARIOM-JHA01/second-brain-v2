import os
import io
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Optional
import PyPDF2

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_api_key = os.getenv("SUPABASE_API_KEY")

supabase: Client = create_client(supabase_url, supabase_api_key)

BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")


def get_bucket():
    return supabase.storage.get_bucket(BUCKET_NAME)


def ensure_bucket_exists():
    try:
        supabase.storage.get_bucket(BUCKET_NAME)
    except Exception:
        supabase.storage.create_bucket(BUCKET_NAME, public=True)


def list_folders():
    try:
        response = supabase.storage.list_buckets()
        return response
    except Exception as e:
        print(f"Error listing buckets: {e}")
        return []


def list_files_in_folder(folder_path: str = "") -> List[Dict]:
    try:
        response = supabase.storage.from_(BUCKET_NAME).list(path=folder_path)
        return response
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def upload_file(
    ruta_archivo_local: str = None,
    local_file_path: str = None,
    folder_id: str = None,
    nombre_carpeta: str = None,
    folder_name: str = None,
    destination_path: str = None,
):
    """
    Upload a file to Supabase Storage.

    Args:
        ruta_archivo_local: Local file path (alternative name)
        local_file_path: Local file path
        folder_id: Ignored (kept for compatibility)
        nombre_carpeta: Folder name (alternative name)
        folder_name: Folder name in Supabase
        destination_path: Destination path in storage

    Returns:
        dict: Information about uploaded file
    """
    file_path = ruta_archivo_local or local_file_path

    if not file_path:
        return {"success": False, "error": "No file path provided"}

    folder = nombre_carpeta or folder_name

    try:
        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            return {"success": False, "error": f"File does not exist: {file_path}"}

        file_name = os.path.basename(file_path)

        if folder:
            destination = f"{folder}/{file_name}"
        elif destination_path:
            destination = destination_path
        else:
            destination = file_name

        with open(file_path, "rb") as f:
            file_content = f.read()

        response = supabase.storage.from_(BUCKET_NAME).upload(
            path=destination,
            data=file_content,
            file_options={"content-type": get_content_type(file_name)},
        )

        if response:
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(destination)
            return {
                "success": True,
                "file_id": destination,
                "file_name": file_name,
                "path": destination,
                "web_view_link": public_url,
                "web_content_link": public_url,
                "public_url": public_url,
            }
        return {"success": False, "error": "Upload failed"}

    except Exception as e:
        print(f"Error uploading file: {e}")
        return {"success": False, "error": str(e)}


def download_file(file_path: str, destination_path: str) -> bool:
    try:
        response = supabase.storage.from_(BUCKET_NAME).download(file_path)

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        with open(destination_path, "wb") as f:
            f.write(response)

        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False


def delete_file(file_path: str) -> bool:
    try:
        supabase.storage.from_(BUCKET_NAME).remove([file_path])
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


def get_public_url(file_path: str) -> str:
    return supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)


def get_content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    return mime_types.get(ext, "application/octet-stream")


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return None


def extract_text_from_file(file_path: str) -> Optional[str]:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print(f"Unsupported file type: {ext}")
        return None


if __name__ == "__main__":
    ensure_bucket_exists()

    print("Buckets:", list_folders())

    result = upload_file(
        local_file_path="test.pdf",
        destination_path="test/test.pdf",
        folder_name="documents",
    )
    print("Upload result:", result)
