import cloudinary
import cloudinary.uploader

from agente_rolplay.config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


def upload_to_cloudinary(
    file_path: str,
    public_id: str = None,
    folder: str = None,
    resource_type: str = "auto",
):
    """
    Upload a file to Cloudinary.

    Args:
        file_path (str): Local path to the file
        public_id (str, optional): Custom public ID for the file
        folder (str, optional): Folder in Cloudinary to upload to
        resource_type (str): Resource type - "auto", "image", "video", "raw" (default: "auto")

    Returns:
        dict: Upload result with URL and details
    """
    try:
        upload_params = {}

        if public_id:
            upload_params["public_id"] = public_id

        if folder:
            upload_params["folder"] = folder

        result = cloudinary.uploader.upload(
            file_path, resource_type=resource_type, **upload_params
        )

        return {
            "success": True,
            "public_id": result.get("public_id"),
            "url": result.get("url"),
            "secure_url": result.get("secure_url"),
            "format": result.get("format"),
            "width": result.get("width"),
            "height": result.get("height"),
            "bytes": result.get("bytes"),
            "resource_type": result.get("resource_type"),
        }

    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return {"success": False, "error": str(e)}


def upload_file_to_cloudinary(file_path: str, folder: str = "knowledgebase"):
    """
    Upload a file to Cloudinary with folder support.

    Args:
        file_path (str): Local path to the file
        folder (str): Folder in Cloudinary (default: knowledgebase)

    Returns:
        dict: Upload result with URL and details
    """
    return upload_to_cloudinary(file_path, folder=folder, resource_type="auto")
