import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


def upload_to_cloudinary(file_path, public_id=None, folder=None):
    """
    Upload a file to Cloudinary.

    Args:
        file_path (str): Local path to the file
        public_id (str, optional): Custom public ID for the file
        folder (str, optional): Folder in Cloudinary to upload to

    Returns:
        dict: Upload result with URL and details
    """
    try:
        upload_params = {
            "resource_type": "image",
        }

        if public_id:
            upload_params["public_id"] = public_id

        if folder:
            upload_params["folder"] = folder

        result = cloudinary.uploader.upload(file_path, **upload_params)

        return {
            "success": True,
            "public_id": result.get("public_id"),
            "url": result.get("url"),
            "secure_url": result.get("secure_url"),
            "format": result.get("format"),
            "width": result.get("width"),
            "height": result.get("height"),
            "bytes": result.get("bytes"),
        }

    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return {"success": False, "error": str(e)}


def upload_file_to_cloudinary(file_path, folder="knowledgebase"):
    """
    Upload a file to Cloudinary with folder support.

    Args:
        file_path (str): Local path to the file
        folder (str): Folder in Cloudinary (default: knowledgebase)

    Returns:
        dict: Upload result with URL and details
    """
    return upload_to_cloudinary(file_path, folder=folder)
