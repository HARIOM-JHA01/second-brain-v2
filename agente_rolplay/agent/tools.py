# python3 tools.py

tools = [
    {
        "name": "informacion_general",
        "description": "Function to offer general business information / answer customer questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Customer question about the business / general doubts about Rolplay.",
                }
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "actualizar_drive",
        "description": "Function to create folders and upload files to Google Drive",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_archivo": {
                    "type": "string",
                    "description": "Name of the file the user wants to create.",
                },
                "tipo_documento": {
                    "type": "string",
                    "description": "Can be an xlsx, pdf, docx, pptx file. ONLY THOSE OPTIONS ARE ALLOWED",
                },
            },
            "required": ["nombre_archivo", "tipo_documento"],
        },
    },
    {
        "name": "saludar_cliente",
        "description": "Function to greet the customer and introduce as virtual assistant",
        "input_schema": {
            "type": "object",
            "properties": {
                "saludo": {
                    "type": "string",
                    "description": "Initial greeting from the customer",
                }
            },
            "required": ["saludo"],
        },
    },
]
