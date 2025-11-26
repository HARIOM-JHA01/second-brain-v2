# python3 tools.py

tools = [
    {
        'name': 'informacion_general',
        'description': 'Función para ofrecer información general del negocio / responder dudas al cliente.',
        'input_schema': {
                'type': 'object',
                'properties': {
                    'consulta': {
                        'type': 'string',
                        'description': 'Consulta del cliente sobre el negocio / dudas generales.'
                    }
                },
            'required': ['consulta']
        }
    },
    {
        'name': 'actualizar_drive',
        'description': 'Función para crear carpetas y subir archivos en Google Drive',
        'input_schema': {
            'type': 'object',
            'properties': {
                'nombre_archivo': {
                    'type': 'string',
                    'description': 'Nombre del archivo que desea crear el usuario.'
                },
                'tipo_documento': {
                    'type': 'string',
                    'description': 'Puede ser un archivo xlsx, pdf, docx, pptx. SOLO PUEDEN SER ESAS OPCIONES'
                }
            },
            'required': ['nombre_archivo', 'tipo_documento']
        }
    },
    {
        'name': 'saludar_cliente',
        'description': 'Función para saludar al cliente y presentarse como asistente virtual',
        'input_schema': {
				'type': 'object',
                'properties': {
					'saludo': {
                        'type': 'string',
						'description': 'Saludo inicial del cliente'
					}
		        },
                'required': ['saludo']
	    }
    }
]




