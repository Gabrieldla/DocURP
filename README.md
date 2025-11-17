# Plataforma de Gestión de Documentos URP

Una plataforma web desarrollada con FastHTML que permite a usuarios con correo institucional @urp.edu.pe registrarse, iniciar sesión y gestionar sus documentos (PDF, Word, Excel).

## 🚀 Características

- ✅ Registro de usuarios con validación de correo @urp.edu.pe
- 🔐 Sistema de autenticación seguro con JWT y bcrypt
- 📄 Subida de documentos (PDF, Word, Excel)
- 👁️ Visualización de documentos PDF en el navegador
- 📥 Descarga de todos los tipos de documentos
- 💾 Almacenamiento seguro por usuario
- 🎨 Interfaz moderna y responsiva

## 📋 Requisitos Previos

- Python 3.13 o superior
- pip (gestor de paquetes de Python)

## 🔧 Instalación

1. **Clonar o descargar el proyecto**

2. **Crear y activar el entorno virtual** (ya está configurado)
   ```bash
   # En Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```

3. **Las dependencias ya están instaladas:**
   - python-fasthtml
   - python-multipart
   - uvicorn
   - starlette
   - jinja2
   - python-dotenv
   - bcrypt
   - pyjwt
   - aiosqlite
   - openpyxl
   - python-docx
   - pypdf2

4. **Configurar variables de entorno** (opcional)
   ```bash
   # Copiar el archivo de ejemplo
   cp .env.example .env
   
   # Editar .env y cambiar SECRET_KEY por una clave segura
   ```

## 🚀 Uso

1. **Iniciar el servidor**
   ```bash
   python app.py
   ```
   
   O con uvicorn directamente:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Acceder a la aplicación**
   
   Abrir el navegador en: `http://localhost:8000`

3. **Registrar un usuario**
   - Usar un correo con dominio @urp.edu.pe
   - Ejemplo: `estudiante@urp.edu.pe`
   - Crear una contraseña segura

4. **Subir documentos**
   - Iniciar sesión con las credenciales
   - En el dashboard, seleccionar un archivo
   - Agregar una descripción opcional
   - Hacer clic en "Subir Documento"

5. **Gestionar documentos**
   - Ver: Previsualizar PDFs en el navegador
   - Descargar: Obtener cualquier documento
   - Los archivos se organizan por usuario

## 📁 Estructura del Proyecto

```
IA-TAREA/
├── app.py                 # Aplicación principal con rutas
├── database.py            # Funciones de base de datos
├── .env.example          # Plantilla de configuración
├── .gitignore            # Archivos a ignorar en git
├── static/
│   └── css/
│       └── style.css     # Estilos de la aplicación
├── uploads/              # Documentos subidos (por usuario)
├── documents.db          # Base de datos SQLite (se crea automáticamente)
└── README.md             # Este archivo
```

## 🔒 Seguridad

- Las contraseñas se hashean con bcrypt
- Autenticación mediante JWT con cookies httponly
- Validación estricta del dominio de correo @urp.edu.pe
- Archivos organizados por usuario (aislamiento)
- Solo se permiten tipos de archivo específicos

## 📝 Tipos de Archivos Permitidos

- 📄 PDF (.pdf)
- 📝 Word (.doc, .docx)
- 📊 Excel (.xls, .xlsx)

## 🛠️ Tecnologías Utilizadas

- **FastHTML**: Framework web moderno para Python
- **SQLite**: Base de datos ligera
- **bcrypt**: Hash de contraseñas
- **JWT**: Tokens de autenticación
- **Uvicorn**: Servidor ASGI de alto rendimiento

## 🐛 Solución de Problemas

### El servidor no inicia
```bash
# Verificar que el puerto 8000 esté libre
netstat -ano | findstr :8000

# Usar otro puerto si es necesario
uvicorn app:app --port 8001
```

### Error al subir archivos
- Verificar que la carpeta `uploads/` existe
- Comprobar permisos de escritura
- Verificar el tamaño del archivo

### No se puede registrar
- Asegurar que el correo termine en @urp.edu.pe
- Verificar que el correo no esté ya registrado

## 📧 Contacto

Para dudas o sugerencias sobre este proyecto, contactar al administrador del sistema.

## 📄 Licencia

Este proyecto es de uso educativo para la Universidad Ricardo Palma.
