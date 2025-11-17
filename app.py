from fasthtml.common import *
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
from starlette.responses import FileResponse
from dotenv import load_dotenv
from database import init_db, signup_user, signin_user, get_user_profile, get_profile_by_email, get_profile_by_student_code, save_document, get_user_documents, delete_document, reset_password_email
from supabase import create_client

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "tu-clave-secreta-muy-segura-cambiala")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls'}

# Supabase Storage bucket name
STORAGE_BUCKET = "documents"

# Check if running in production (Vercel sets VERCEL env var)
IS_PRODUCTION = os.getenv("VERCEL") is not None
BASE_URL = os.getenv("BASE_URL", "https://doc-urp.vercel.app" if IS_PRODUCTION else "http://localhost:5001")

app, rt = fast_app(
    live=not IS_PRODUCTION,  # Disable live-reload in production
    hdrs=(
        Script(src='https://cdn.tailwindcss.com'),
        Link(rel='preconnect', href='https://fonts.googleapis.com'),
        Link(rel='preconnect', href='https://fonts.gstatic.com', crossorigin='anonymous'),
        Link(rel='stylesheet', href='https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap'),
        Script("""
            tailwind.config = {
                theme: {
                    extend: {
                        colors: {
                            'brand': '#34B27B',
                            'brand-dark': '#11181C',
                            'brand-light': '#F8F9FA',
                            'primary': '#34B27B',
                            'primary-dark': '#2A9063',
                        },
                        fontFamily: {
                            'sans': ['Outfit', 'sans-serif'],
                        }
                    }
                }
            }
        """),
        Link(rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'),
        Style("""
            :root {
                --background: #F8F9FA;
                --foreground: #11181C;
                --card: #FFFFFF;
                --card-foreground: #11181C;
                --primary: #34B27B;
                --primary-foreground: #FFFFFF;
                --secondary: #F8F9FA;
                --secondary-foreground: #11181C;
                --border: #E5E7EB;
                --input: #FFFFFF;
                --radius: 0.5rem;
            }
            
            body {
                font-family: 'Outfit', sans-serif;
            }
        """),
    )
)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Utility functions
def get_current_user(request):
    """Get current user from Supabase session"""
    access_token = request.cookies.get('sb_access_token')
    if access_token:
        try:
            response = supabase_client.auth.get_user(access_token)
            return response.user if response and response.user else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    return None

def is_urp_email(email: str) -> bool:
    """Validate that email is from @urp.edu.pe domain"""
    return email.lower().endswith('@urp.edu.pe')

# Routes
@rt('/')
def get(request):
    """Home page - redirect to login or dashboard"""
    current_user = get_current_user(request)
    if current_user:
        return RedirectResponse('/dashboard', status_code=303)
    return RedirectResponse('/login', status_code=303)

@rt('/register')
def get():
    """Registration page"""
    return Div(
        # Background with blur effect
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        
        # Main container
        Div(
            Div(
                # Logo/Brand section
                Div(
                    Div(
                        Svg(
                            """<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />""",
                            xmlns='http://www.w3.org/2000/svg',
                            fill='none',
                            viewBox='0 0 24 24',
                            stroke_width='1.5',
                            stroke='currentColor',
                            cls='w-12 h-12 text-brand'
                        ),
                        cls='flex justify-center mb-3'
                    ),
                    H1('DocURP', cls='text-3xl font-bold text-white text-center mb-2 tracking-tight font-sans'),
                    P('Crea tu cuenta institucional', cls='text-brand/90 text-center text-sm font-light'),
                    cls='mb-8'
                ),
                
                # Form container
                Div(
                    H2('Registro', cls='text-2xl font-bold text-white mb-8 text-center'),
                    
                    Form(
                        # Name field
                        Div(
                            Label('Nombre completo', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='text',
                                    name='name',
                                    placeholder='Juan Pérez',
                                    required=True,
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-4'
                        ),
                        
                        # Student Code field
                        Div(
                            Label('Código de estudiante', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Input(
                                type='text',
                                name='student_code',
                                placeholder='202220427',
                                required=True,
                                pattern='[0-9]{9}',
                                maxlength='9',
                                cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                            ),
                            cls='mb-4'
                        ),
                        
                        # Email field
                        Div(
                            Label('Correo institucional', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='email',
                                    name='email',
                                    placeholder='correo@urp.edu.pe',
                                    required=True,
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-4'
                        ),
                        
                        # Password field
                        Div(
                            Label('Contraseña (mínimo 6 caracteres)', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='password',
                                    name='password',
                                    placeholder='••••••••',
                                    required=True,
                                    minlength='6',
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-4'
                        ),
                        
                        # Confirm password field
                        Div(
                            Label('Confirmar contraseña', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='password',
                                    name='confirm_password',
                                    placeholder='••••••••',
                                    required=True,
                                    minlength='6',
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-6'
                        ),
                        
                        # Submit button
                        Button(
                            'Crear Cuenta',
                            type='submit',
                            cls='w-full bg-brand hover:bg-primary-dark text-white font-semibold py-3.5 rounded-xl transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        
                        action='/register',
                        method='post'
                    ),
                    
                    # Divider
                    Div(
                        Div(cls='flex-1 border-t border-white/10'),
                        Span('o', cls='px-4 text-gray-400 text-sm'),
                        Div(cls='flex-1 border-t border-white/10'),
                        cls='flex items-center my-6'
                    ),
                    
                    # Login link
                    Div(
                        Span('¿Ya tienes cuenta? ', cls='text-gray-400 text-sm'),
                        A('Inicia sesión', href='/login', cls='text-brand hover:text-brand/80 font-semibold text-sm transition'),
                        cls='text-center'
                    ),
                    
                    cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 w-full max-w-md border border-white/10'
                ),
                
                cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-12'
            ),
            cls='relative'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/register')
async def post(email: str, password: str, confirm_password: str, name: str, student_code: str):
    """Handle registration with Supabase Auth"""
    # Validate password length
    if len(password) < 6:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-lock text-orange-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('La contraseña debe tener al menos 6 caracteres', cls='text-gray-600 text-center mb-6'),
                            A(
                                I(cls='fas fa-arrow-left mr-2'),
                                'Volver al registro',
                                href='/register',
                                cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Validate @urp.edu.pe email
    if not is_urp_email(email):
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%239C92AC\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-exclamation-circle text-red-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Solo se permiten correos institucionales @urp.edu.pe', cls='text-gray-600 text-center mb-6'),
                            A(
                                I(cls='fas fa-arrow-left mr-2'),
                                'Volver al registro',
                                href='/register',
                                cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Validate password match
    if password != confirm_password:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%239C92AC\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-lock text-red-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Las contraseñas no coinciden', cls='text-gray-600 text-center mb-6'),
                            A(
                                I(cls='fas fa-arrow-left mr-2'),
                                'Volver al registro',
                                href='/register',
                                cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Check if email already exists
    existing_user = await get_profile_by_email(email)
    if existing_user:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-user-times text-orange-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Este correo ya está registrado', cls='text-gray-600 text-center mb-6'),
                            Div(
                                A(
                                    I(cls='fas fa-arrow-left mr-2'),
                                    'Volver al registro',
                                    href='/register',
                                    cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30 mb-3'
                                ),
                                A(
                                    I(cls='fas fa-sign-in-alt mr-2'),
                                    'Iniciar sesión',
                                    href='/login',
                                    cls='inline-flex items-center justify-center w-full bg-white text-brand-dark py-3 rounded-xl font-semibold hover:bg-gray-50 transition duration-200 border border-brand/30'
                                ),
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Check if student code already exists
    existing_code = await get_profile_by_student_code(student_code)
    if existing_code:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%239C92AC\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-id-card text-orange-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Este código de estudiante ya está registrado', cls='text-gray-600 text-center mb-6'),
                            A(
                                I(cls='fas fa-arrow-left mr-2'),
                                'Volver al registro',
                                href='/register',
                                cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Create user with Supabase Auth
    result = await signup_user(email, password, name, student_code)
    
    if not result:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-exclamation-circle text-red-500 text-6xl mb-4'),
                            H2('Error de Registro', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Error al crear la cuenta. Por favor intenta de nuevo.', cls='text-gray-600 text-center mb-6'),
                            A(
                                I(cls='fas fa-arrow-left mr-2'),
                                'Volver al registro',
                                href='/register',
                                cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    return Div(
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%239C92AC\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        Div(
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-check-circle text-green-500 text-7xl mb-6 animate-bounce'),
                            cls='text-center'
                        ),
                        H2('¡Registro Exitoso!', cls='text-3xl font-bold text-gray-800 mb-4 text-center'),
                        P('Revisa tu correo para confirmar tu cuenta', cls='text-gray-600 text-center mb-4'),
                        P('Te hemos enviado un email de verificación', cls='text-sm text-gray-500 text-center mb-8'),
                        Div(
                            Div(
                                I(cls='fas fa-envelope text-brand text-lg'),
                                cls='flex items-center justify-center mb-2'
                            ),
                            P(email, cls='text-sm text-gray-500 font-mono'),
                            cls='bg-brand/10 rounded-xl p-4 mb-6 text-center'
                        ),
                        A(
                            I(cls='fas fa-sign-in-alt mr-2'),
                            'Iniciar Sesión',
                            href='/login',
                            cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3.5 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                    ),
                    cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                ),
                cls='relative z-10 flex items-center justify-center min-h-screen px-4'
            ),
            cls='relative'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/login')
def get():
    """Login page"""
    return Div(
        # Background with blur effect
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        
        # Main container
        Div(
            Div(
                # Logo/Brand section
                Div(
                    Div(
                        Svg(
                            """<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />""",
                            xmlns='http://www.w3.org/2000/svg',
                            fill='none',
                            viewBox='0 0 24 24',
                            stroke_width='1.5',
                            stroke='currentColor',
                            cls='w-12 h-12 text-brand'
                        ),
                        cls='flex justify-center mb-3'
                    ),
                    H1('DocURP', cls='text-3xl font-bold text-white text-center mb-2 tracking-tight font-sans'),
                    P('Tu plataforma de documentos', cls='text-brand/90 text-center text-sm font-light'),
                    cls='mb-8'
                ),
                
                # Form container
                Div(
                    H2('Iniciar Sesión', cls='text-2xl font-bold text-white mb-8 text-center'),
                    
                    Form(
                        # Email field
                        Div(
                            Label('Correo electrónico', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='email',
                                    name='email',
                                    placeholder='correo@urp.edu.pe',
                                    required=True,
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3.5 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-5'
                        ),
                        
                        # Password field
                        Div(
                            Label('Contraseña', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='password',
                                    name='password',
                                    placeholder='••••••••',
                                    required=True,
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3.5 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-8'
                        ),
                        
                        # Submit button
                        Button(
                            'Iniciar Sesión',
                            type='submit',
                            cls='w-full bg-brand hover:bg-primary-dark text-white font-semibold py-3.5 rounded-xl transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        
                        action='/login',
                        method='post'
                    ),
                    
                    # Divider
                    Div(
                        Div(cls='flex-1 border-t border-white/10'),
                        Span('o', cls='px-4 text-gray-400 text-sm'),
                        Div(cls='flex-1 border-t border-white/10'),
                        cls='flex items-center my-6'
                    ),
                    
                    # Forgot password link
                    Div(
                        A('¿Olvidaste tu contraseña?', href='/forgot-password', cls='text-brand hover:text-brand/80 text-sm transition'),
                        cls='text-center mb-4'
                    ),
                    
                    # Register link
                    Div(
                        Span('¿No tienes cuenta? ', cls='text-gray-400 text-sm'),
                        A('Regístrate aquí', href='/register', cls='text-brand hover:text-brand/80 font-semibold text-sm transition'),
                        cls='text-center'
                    ),
                    
                    cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 w-full max-w-md border border-white/10'
                ),
                
                cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-12'
            ),
            cls='relative'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/login')
async def post(email: str, password: str):
    """Handle login with Supabase Auth"""
    auth_response = await signin_user(email, password)
    
    if not auth_response or not auth_response.session:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-times-circle text-red-500 text-6xl mb-4'),
                            H2('Error de Inicio de Sesión', cls='text-2xl font-bold text-gray-800 mb-4'),
                            P('Correo o contraseña incorrectos', cls='text-gray-600 text-center mb-6'),
                            Div(
                                A(
                                    I(cls='fas fa-redo mr-2'),
                                    'Volver a intentar',
                                    href='/login',
                                    cls='inline-flex items-center justify-center w-full bg-brand hover:bg-primary-dark text-white py-3 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30 mb-3'
                                ),
                                A(
                                    I(cls='fas fa-user-plus mr-2'),
                                    'Crear cuenta',
                                    href='/register',
                                    cls='inline-flex items-center justify-center w-full bg-white text-brand-dark py-3 rounded-xl font-semibold hover:bg-gray-50 transition duration-200 border border-brand/30'
                                ),
                            ),
                            cls='text-center'
                        ),
                        cls='bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-10 max-w-md w-full border border-white/20'
                    ),
                    cls='relative z-10 flex items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Set Supabase session cookies
    response = RedirectResponse('/dashboard', status_code=303)
    response.set_cookie(
        key='sb_access_token',
        value=auth_response.session.access_token,
        httponly=True,
        max_age=auth_response.session.expires_in,
        secure=True,
        samesite='lax'
    )
    response.set_cookie(
        key='sb_refresh_token',
        value=auth_response.session.refresh_token,
        httponly=True,
        max_age=7*24*60*60,  # 7 days
        secure=True,
        samesite='lax'
    )
    return response

@rt('/logout')
def get():
    """Logout user"""
    response = RedirectResponse('/login', status_code=303)
    response.delete_cookie('sb_access_token')
    response.delete_cookie('sb_refresh_token')
    return response

@rt('/forgot-password')
def get():
    """Forgot password page"""
    return Div(
        # Background with blur effect
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        
        # Main container
        Div(
            Div(
                # Logo/Brand section
                Div(
                    Div(
                        Svg(
                            """<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />""",
                            xmlns='http://www.w3.org/2000/svg',
                            fill='none',
                            viewBox='0 0 24 24',
                            stroke_width='1.5',
                            stroke='currentColor',
                            cls='w-12 h-12 text-brand'
                        ),
                        cls='flex justify-center mb-3'
                    ),
                    H1('Recuperar Contraseña', cls='text-3xl font-bold text-white text-center mb-2 tracking-tight font-sans'),
                    P('Te enviaremos un enlace de recuperación', cls='text-brand/90 text-center text-sm font-light'),
                    cls='mb-8'
                ),
                
                # Form container
                Div(
                    Form(
                        # Email field
                        Div(
                            Label('Correo electrónico', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='email',
                                    name='email',
                                    placeholder='correo@urp.edu.pe',
                                    required=True,
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3.5 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-6'
                        ),
                        
                        # Submit button
                        Button(
                            'Enviar enlace de recuperación',
                            type='submit',
                            cls='w-full bg-brand hover:bg-primary-dark text-white font-semibold py-3.5 rounded-xl transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        
                        action='/forgot-password',
                        method='post'
                    ),
                    
                    # Divider
                    Div(
                        Div(cls='flex-1 border-t border-white/10'),
                        Span('o', cls='px-4 text-gray-400 text-sm'),
                        Div(cls='flex-1 border-t border-white/10'),
                        cls='flex items-center my-6'
                    ),
                    
                    # Back to login link
                    Div(
                        A(
                            Svg(
                                """<path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />""",
                                xmlns='http://www.w3.org/2000/svg',
                                fill='none',
                                viewBox='0 0 24 24',
                                stroke_width='1.5',
                                stroke='currentColor',
                                cls='w-4 h-4 inline mr-2'
                            ),
                            'Volver al inicio de sesión',
                            href='/login',
                            cls='text-brand hover:text-brand/80 text-sm transition inline-flex items-center'
                        ),
                        cls='text-center'
                    ),
                    
                    cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 w-full max-w-md border border-white/10'
                ),
                
                cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-12'
            ),
            cls='relative'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/forgot-password')
async def post(email: str, request):
    """Handle password reset email"""
    # Get the correct base URL from the request or environment
    host = request.headers.get('host', 'localhost:5001')
    protocol = 'https' if IS_PRODUCTION else 'http'
    redirect_url = f"{protocol}://{host}/reset-password"
    
    # Send reset email with custom redirect
    result = await reset_password_email(email, redirect_to=redirect_url)
    
    if result:
        # Success page
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        I(cls='fas fa-envelope text-brand text-6xl mb-4'),
                        H2('Correo Enviado', cls='text-2xl font-bold text-white mb-4'),
                        P(f'Se ha enviado un enlace de recuperación a {email}', cls='text-gray-300 text-center mb-6 max-w-md'),
                        P('Revisa tu bandeja de entrada y sigue las instrucciones del correo.', cls='text-gray-400 text-center text-sm mb-6 max-w-md'),
                        A(
                            I(cls='fas fa-arrow-left mr-2'),
                            'Volver al inicio de sesión',
                            href='/login',
                            cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                    ),
                    cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    else:
        # Error page
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        I(cls='fas fa-times-circle text-red-500 text-6xl mb-4'),
                        H2('Error al Enviar', cls='text-2xl font-bold text-white mb-4'),
                        P('No se pudo enviar el correo de recuperación', cls='text-gray-300 text-center mb-2'),
                        P('Verifica que el correo esté registrado o intenta más tarde.', cls='text-gray-400 text-center text-sm mb-6'),
                        A(
                            I(cls='fas fa-redo mr-2'),
                            'Volver a intentar',
                            href='/forgot-password',
                            cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                    ),
                    cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )

@rt('/reset-password')
def get(request):
    """Reset password page - user arrives here from email link"""
    # Get access_token from URL params (Supabase sends it as #access_token=... but browsers convert to query param)
    return Div(
        # Background with blur effect
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        
        # Main container
        Div(
            Div(
                # Logo/Brand section
                Div(
                    Div(
                        Svg(
                            """<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 013-3h3a3 3 0 013 3m-6 0v-1.5m0 1.5h6m-6 0H9m12 0v1.5m0-1.5h1.5m-1.5 0H21m-3 6h.008v.008H18V11.25zm-3 0h.008v.008H15V11.25z" />""",
                            xmlns='http://www.w3.org/2000/svg',
                            fill='none',
                            viewBox='0 0 24 24',
                            stroke_width='1.5',
                            stroke='currentColor',
                            cls='w-12 h-12 text-brand'
                        ),
                        cls='flex justify-center mb-3'
                    ),
                    H1('Nueva Contraseña', cls='text-3xl font-bold text-white text-center mb-2 tracking-tight font-sans'),
                    P('Crea una contraseña segura', cls='text-brand/90 text-center text-sm font-light'),
                    cls='mb-8'
                ),
                
                # Form container
                Div(
                    Form(
                        # New Password field
                        Div(
                            Label('Nueva contraseña', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='password',
                                    name='password',
                                    placeholder='••••••••',
                                    required=True,
                                    minlength='6',
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3.5 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            P('Mínimo 6 caracteres', cls='text-xs text-gray-400 mt-1'),
                            cls='mb-5'
                        ),
                        
                        # Confirm Password field
                        Div(
                            Label('Confirmar contraseña', cls='block text-sm font-medium text-gray-300 mb-2'),
                            Div(
                                Div(
                                    Svg(
                                        """<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />""",
                                        xmlns='http://www.w3.org/2000/svg',
                                        fill='none',
                                        viewBox='0 0 24 24',
                                        stroke_width='1.5',
                                        stroke='currentColor',
                                        cls='w-5 h-5 text-brand'
                                    ),
                                    cls='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'
                                ),
                                Input(
                                    type='password',
                                    name='confirm_password',
                                    placeholder='••••••••',
                                    required=True,
                                    minlength='6',
                                    cls='w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl pl-10 pr-4 py-3.5 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition duration-200'
                                ),
                                cls='relative'
                            ),
                            cls='mb-8'
                        ),
                        
                        # Submit button
                        Button(
                            'Actualizar contraseña',
                            type='submit',
                            cls='w-full bg-brand hover:bg-primary-dark text-white font-semibold py-3.5 rounded-xl transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        
                        action='/reset-password',
                        method='post'
                    ),
                    
                    cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 w-full max-w-md border border-white/10'
                ),
                
                cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-12'
            ),
            cls='relative'
        ),
        Script("""
            // Supabase sends token in URL hash (#access_token=...), extract and store
            window.addEventListener('DOMContentLoaded', function() {
                const hash = window.location.hash.substring(1);
                const params = new URLSearchParams(hash);
                const accessToken = params.get('access_token');
                
                if (accessToken) {
                    // Store token in sessionStorage for form submission
                    sessionStorage.setItem('reset_token', accessToken);
                    // Clean URL
                    history.replaceState(null, '', window.location.pathname);
                }
            });
            
            // Add token to form submission
            document.querySelector('form').addEventListener('submit', function(e) {
                const token = sessionStorage.getItem('reset_token');
                if (token) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'access_token';
                    input.value = token;
                    this.appendChild(input);
                }
            });
        """),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/reset-password')
async def post(password: str, confirm_password: str, access_token: str = None):
    """Handle password reset"""
    # Validate passwords match
    if password != confirm_password:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        I(cls='fas fa-times-circle text-red-500 text-6xl mb-4'),
                        H2('Error', cls='text-2xl font-bold text-white mb-4'),
                        P('Las contraseñas no coinciden', cls='text-gray-300 text-center mb-6'),
                        A(
                            I(cls='fas fa-redo mr-2'),
                            'Volver a intentar',
                            href='/reset-password',
                            cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                    ),
                    cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    if not access_token:
        return Div(
            Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
            Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
            Div(
                Div(
                    Div(
                        I(cls='fas fa-exclamation-triangle text-yellow-500 text-6xl mb-4'),
                        H2('Enlace Inválido', cls='text-2xl font-bold text-white mb-4'),
                        P('El enlace de recuperación ha expirado o es inválido', cls='text-gray-300 text-center mb-6 max-w-md'),
                        A(
                            'Solicitar nuevo enlace',
                            href='/forgot-password',
                            cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                        ),
                        cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                    ),
                    cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
                ),
                cls='relative'
            ),
            cls='relative min-h-screen overflow-hidden'
        )
    
    # Update password using Supabase
    try:
        # Set session with the access token
        supabase_client.auth.set_session(access_token, access_token)
        # Update password
        response = supabase_client.auth.update_user({"password": password})
        
        if response:
            # Success
            return Div(
                Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
                Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-check-circle text-brand text-6xl mb-4'),
                            H2('¡Contraseña Actualizada!', cls='text-2xl font-bold text-white mb-4'),
                            P('Tu contraseña ha sido actualizada exitosamente', cls='text-gray-300 text-center mb-6'),
                            A(
                                'Iniciar sesión',
                                href='/login',
                                cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                            ),
                            cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                        ),
                        cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
                    ),
                    cls='relative'
                ),
                cls='relative min-h-screen overflow-hidden'
            )
    except Exception as e:
        print(f"Error updating password: {e}")
    
    # Error page
    return Div(
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        Div(
            Div(
                Div(
                    I(cls='fas fa-times-circle text-red-500 text-6xl mb-4'),
                    H2('Error', cls='text-2xl font-bold text-white mb-4'),
                    P('No se pudo actualizar la contraseña', cls='text-gray-300 text-center mb-6'),
                    A(
                        'Solicitar nuevo enlace',
                        href='/forgot-password',
                        cls='inline-flex items-center justify-center bg-brand hover:bg-primary-dark text-white py-3 px-8 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30'
                    ),
                    cls='bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl p-10 text-center border border-white/10 max-w-md'
                ),
                cls='relative z-10 flex flex-col items-center justify-center min-h-screen px-4'
            ),
            cls='relative'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/dashboard')
async def get(request):
    """Dashboard - main page for document management"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse('/login', status_code=303)
    
    # Get user profile and documents
    profile = await get_user_profile(current_user.id)
    if not profile:
        # Profile not found, logout and redirect to login
        response = RedirectResponse('/login', status_code=303)
        response.delete_cookie('sb_access_token')
        response.delete_cookie('sb_refresh_token')
        return response
    
    documents = await get_user_documents(current_user.id)
    
    return Div(
        # Background
        Div(cls='absolute inset-0 bg-gradient-to-br from-brand-dark via-gray-900 to-brand-dark'),
        Div(cls='absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%2334B27B\' fill-opacity=\'0.03\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")]'),
        
        Div(
            # Header
            Div(
                Div(
                    Div(
                        H1(f"Hola, {profile['name']}", cls='text-2xl font-bold text-white font-sans'),
                        P(profile['email'], cls='text-sm text-gray-400'),
                    ),
                    A(
                        I(cls='fas fa-sign-out-alt mr-2'),
                        'Cerrar Sesión',
                        href='/logout',
                        cls='inline-flex items-center bg-red-500 hover:bg-red-600 text-white px-5 py-2.5 rounded-xl font-semibold transition transform hover:scale-105 shadow-lg'
                    ),
                    cls='flex justify-between items-center'
                ),
                cls='bg-white/5 backdrop-blur-xl shadow-lg rounded-2xl p-6 mb-8 border border-white/10'
            ),
            
            # Upload Section
            Div(
                Div(
                    I(cls='fas fa-cloud-upload-alt text-brand text-3xl mb-4'),
                    H2('Subir Documento', cls='text-2xl font-bold text-white mb-2 font-sans'),
                    P('Sube archivos PDF, Word o Excel', cls='text-gray-400 text-sm mb-6'),
                    cls='text-center'
                ),
                Form(
                    Div(
                        Label(
                            Div(
                                I(cls='fas fa-file-upload text-4xl text-brand mb-3', id='upload-icon'),
                                P('Click para seleccionar o arrastra tu archivo aquí', cls='text-sm text-gray-300 mb-1', id='upload-text'),
                                P('PDF, Word, Excel (máx. 10MB)', cls='text-xs text-gray-500', id='upload-hint'),
                                P('', cls='text-sm text-brand font-semibold mt-2', id='file-name'),
                                cls='text-center py-8'
                            ),
                            Input(
                                type='file',
                                name='file',
                                accept='.pdf,.doc,.docx,.xls,.xlsx',
                                required=True,
                                cls='hidden',
                                id='file-input',
                                onchange="document.getElementById('file-name').textContent = this.files[0]?.name || ''; document.getElementById('upload-text').textContent = this.files[0] ? 'Archivo seleccionado:' : 'Click para seleccionar o arrastra tu archivo aquí';"
                            ),
                            cls='block w-full border-2 border-dashed border-white/20 rounded-2xl hover:border-brand transition cursor-pointer bg-white/5 hover:bg-white/10',
                            **{'for': 'file-input'}
                        ),
                        cls='mb-5'
                    ),
                    Div(
                        Label('Descripción (opcional)', cls='block text-sm font-medium text-gray-300 mb-2'),
                        Textarea(
                            name='description',
                            placeholder='Agrega una descripción para tu documento...',
                            rows='3',
                            cls='w-full px-4 py-3 bg-white/5 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition resize-none'
                        ),
                        cls='mb-6'
                    ),
                    Button(
                        I(cls='fas fa-upload mr-2'),
                        'Subir Documento',
                        type='submit',
                        cls='w-full bg-brand hover:bg-primary-dark text-white py-3.5 rounded-xl font-semibold transform hover:scale-[1.02] transition duration-200 shadow-lg shadow-brand/30 inline-flex items-center justify-center'
                    ),
                    action='/upload',
                    method='post',
                    enctype='multipart/form-data'
                ),
                cls='bg-white/5 backdrop-blur-xl shadow-lg rounded-2xl p-8 mb-8 border border-white/10'
            ),
            
            # Documents List by Type
            *([
                # Separate documents by type
                Div(
                    Div(
                        Div(
                            I(cls='fas fa-folder-open text-brand text-2xl mr-3'),
                            H2('Mis Documentos', cls='text-2xl font-bold text-white font-sans'),
                            cls='flex items-center'
                        ),
                        # Filters
                        Div(
                            # Search bar
                            Div(
                                Div(
                                    I(cls='fas fa-search text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2'),
                                    cls='relative'
                                ),
                                Input(
                                    type='text',
                                    id='search-input',
                                    placeholder='Buscar documentos...',
                                    oninput='searchDocs()',
                                    cls='w-full md:w-64 pl-10 pr-4 py-2 bg-white/5 border border-white/10 text-white placeholder-gray-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition'
                                ),
                                cls='relative mb-3 md:mb-0'
                            ),
                            # Filters
                            Div(
                                Button(
                                    I(cls='fas fa-filter mr-2'),
                                    'Todos',
                                    onclick="filterDocs('all')",
                                    id='filter-all',
                                    cls='px-4 py-2 bg-brand text-white rounded-lg font-semibold transition hover:bg-primary-dark'
                                ),
                                Button(
                                    I(cls='fas fa-file-pdf mr-2'),
                                    'PDF',
                                    onclick="filterDocs('pdf')",
                                    id='filter-pdf',
                                    cls='px-4 py-2 bg-white/10 text-gray-300 rounded-lg font-semibold transition hover:bg-white/20'
                                ),
                                Button(
                                    I(cls='fas fa-file-word mr-2'),
                                    'Word',
                                    onclick="filterDocs('word')",
                                    id='filter-word',
                                    cls='px-4 py-2 bg-white/10 text-gray-300 rounded-lg font-semibold transition hover:bg-white/20'
                                ),
                                Button(
                                    I(cls='fas fa-file-excel mr-2'),
                                    'Excel',
                                    onclick="filterDocs('excel')",
                                    id='filter-excel',
                                    cls='px-4 py-2 bg-white/10 text-gray-300 rounded-lg font-semibold transition hover:bg-white/20'
                                ),
                                cls='flex gap-2 flex-wrap'
                            ),
                            cls='flex flex-col md:flex-row gap-3 items-start md:items-center'
                        ),
                        cls='flex justify-between items-center mb-6 flex-wrap gap-4'
                    ),
                    
                    Script("""
                        function filterDocs(type) {
                            // Update button styles
                            const buttons = ['all', 'pdf', 'word', 'excel'];
                            buttons.forEach(btn => {
                                const element = document.getElementById('filter-' + btn);
                                if (btn === type) {
                                    element.className = 'px-4 py-2 bg-brand text-white rounded-lg font-semibold transition hover:bg-primary-dark';
                                } else {
                                    element.className = 'px-4 py-2 bg-white/10 text-gray-300 rounded-lg font-semibold transition hover:bg-white/20';
                                }
                            });
                            
                            // Show/hide categories
                            const categories = document.querySelectorAll('[data-category]');
                            categories.forEach(cat => {
                                const catType = cat.getAttribute('data-category');
                                if (type === 'all' || type === catType) {
                                    cat.style.display = 'block';
                                } else {
                                    cat.style.display = 'none';
                                }
                            });
                            
                            // Clear search when filtering
                            document.getElementById('search-input').value = '';
                        }
                        
                        function searchDocs() {
                            const searchTerm = document.getElementById('search-input').value.toLowerCase();
                            const docCards = document.querySelectorAll('[data-doc-name]');
                            
                            docCards.forEach(card => {
                                const docName = card.getAttribute('data-doc-name').toLowerCase();
                                const docDesc = card.getAttribute('data-doc-desc').toLowerCase();
                                
                                if (docName.includes(searchTerm) || docDesc.includes(searchTerm)) {
                                    card.style.display = 'block';
                                } else {
                                    card.style.display = 'none';
                                }
                            });
                            
                            // Show all categories when searching
                            if (searchTerm) {
                                const categories = document.querySelectorAll('[data-category]');
                                categories.forEach(cat => cat.style.display = 'block');
                            }
                        }
                    """),
                    
                    # Helper function to categorize documents
                    *[
                        Div(
                            H3(
                                I(cls=f'fas fa-file-{category_icon} text-brand mr-2'),
                                category_name,
                                cls='text-xl font-bold text-white mb-4 flex items-center'
                            ),
                            Div(
                                *[Div(
                                    Div(
                                        Div(
                                            Div(
                                                I(cls=f"fas fa-file-{category_icon} text-3xl text-brand"),
                                                cls='flex items-center justify-center w-16 h-16 bg-brand/10 rounded-xl'
                                            ),
                                            Div(
                                                Strong(doc['filename'], cls='text-lg text-white block mb-1 line-clamp-1'),
                                                P((doc['description'][:50] + '...' if doc['description'] and len(doc['description']) > 50 else doc['description']) or 'Sin descripción', cls='text-sm text-gray-400 mb-2 line-clamp-1'),
                                                Div(
                                                    Span(
                                                        I(cls='fas fa-calendar text-brand text-xs mr-1'),
                                                        doc['uploaded_at'][:10],
                                                        cls='text-xs text-gray-400 mr-4'
                                                    ),
                                                    Span(
                                                        I(cls='fas fa-hdd text-brand text-xs mr-1'),
                                                        f"{doc['file_size'] / 1024:.1f} KB",
                                                        cls='text-xs text-gray-400'
                                                    ),
                                                    cls='flex items-center'
                                                ),
                                                cls='ml-4 flex-1 min-w-0'
                                            ),
                                            cls='flex items-center flex-1 min-w-0'
                                        ),
                                        Div(
                                            A(
                                                I(cls='fas fa-download'),
                                                href=f"/download/{doc['id']}",
                                                cls='flex items-center justify-center w-10 h-10 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition transform hover:scale-110',
                                                title='Descargar'
                                            ),
                                            Form(
                                                Button(
                                                    I(cls='fas fa-trash'),
                                                    type='submit',
                                                    cls='flex items-center justify-center w-10 h-10 bg-red-500 hover:bg-red-600 text-white rounded-lg transition transform hover:scale-110',
                                                    title='Eliminar',
                                                    onclick='return confirm("¿Estás seguro de eliminar este documento?")'
                                                ),
                                                action=f'/delete/{doc["id"]}',
                                                method='post'
                                            ),
                                            cls='flex gap-2'
                                        ),
                                        cls='flex items-center gap-4'
                                    ),
                                    cls='bg-white/5 backdrop-blur-xl hover:bg-white/10 rounded-2xl p-5 border border-white/10 transition hover:shadow-xl hover:scale-[1.01] duration-200',
                                    **{'data-doc-name': doc['filename'], 'data-doc-desc': doc['description'] or ''}
                                ) for doc in category_docs],
                                cls='space-y-3'
                            ),
                            cls='mb-8',
                            **{'data-category': category_type}
                        ) if category_docs else None
                        for category_name, category_icon, category_docs, category_type in [
                            ('Documentos PDF', 'pdf', [d for d in documents if d['mime_type'] == 'application/pdf'], 'pdf'),
                            ('Documentos Word', 'word', [d for d in documents if 'word' in d['mime_type'].lower() and 'sheet' not in d['mime_type'].lower()], 'word'),
                            ('Hojas de Cálculo Excel', 'excel', [d for d in documents if 'excel' in d['mime_type'].lower() or 'sheet' in d['mime_type'].lower() or 'spreadsheet' in d['mime_type'].lower()], 'excel')
                        ]
                    ],
                    cls='bg-white/5 backdrop-blur-xl shadow-lg rounded-2xl p-8 border border-white/10'
                )
            ] if documents else [
                Div(
                    Div(
                        I(cls='fas fa-folder-open text-brand text-2xl mr-3'),
                        H2('Mis Documentos', cls='text-2xl font-bold text-white font-sans'),
                        cls='flex items-center mb-6'
                    ),
                    Div(
                        I(cls='fas fa-inbox text-gray-600 text-7xl mb-6'),
                        H3('No hay documentos', cls='text-xl font-semibold text-white mb-2'),
                        P('Sube tu primer documento usando el formulario de arriba', cls='text-gray-400'),
                        cls='text-center py-20'
                    ),
                    cls='bg-white/5 backdrop-blur-xl shadow-lg rounded-2xl p-8 border border-white/10'
                )
            ]),
            
            cls='relative z-10 max-w-6xl mx-auto px-4 py-8'
        ),
        cls='relative min-h-screen overflow-hidden'
    )

@rt('/upload')
async def post(request):
    """Handle file upload to Supabase Storage"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse('/login', status_code=303)
    
    form = await request.form()
    file = form.get('file')
    description = form.get('description', '')
    
    if not file or not file.filename:
        return RedirectResponse('/dashboard?error=no_file', status_code=303)
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return RedirectResponse('/dashboard?error=invalid_file', status_code=303)
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_filename = f"{current_user.id}/{timestamp}_{file.filename}"
    
    # Read file content
    content = await file.read()
    
    try:
        # Upload to Supabase Storage
        supabase_client.storage.from_(STORAGE_BUCKET).upload(
            path=safe_filename,
            file=content,
            file_options={"content-type": file.content_type or 'application/octet-stream'}
        )
        
        # Get public URL
        file_url = supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(safe_filename)
        
        # Save to database
        await save_document(
            user_id=current_user.id,
            filename=file.filename,
            stored_filename=safe_filename,
            file_path=file_url,
            file_size=len(content),
            mime_type=file.content_type or 'application/octet-stream',
            description=description
        )
        
        return RedirectResponse('/dashboard', status_code=303)
    except Exception as e:
        print(f"Error uploading file: {e}")
        return RedirectResponse('/dashboard?error=upload_failed', status_code=303)

@rt('/delete/{doc_id}')
async def post(request, doc_id: str):
    """Delete document from Supabase Storage"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse('/login', status_code=303)
    
    documents = await get_user_documents(current_user.id)
    
    # Find document
    doc = next((d for d in documents if d['id'] == doc_id), None)
    if not doc:
        return RedirectResponse('/dashboard', status_code=303)
    
    try:
        # Delete file from Supabase Storage
        supabase_client.storage.from_(STORAGE_BUCKET).remove([doc['stored_filename']])
    except Exception as e:
        print(f"Error deleting file from storage: {e}")
    
    # Delete from database
    from database import delete_document
    await delete_document(doc_id)
    
    return RedirectResponse('/dashboard', status_code=303)

@rt('/download/{doc_id}')
async def get(request, doc_id: str):
    """Download document from Supabase Storage"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse('/login', status_code=303)
    
    documents = await get_user_documents(current_user.id)
    
    # Find document
    doc = next((d for d in documents if d['id'] == doc_id), None)
    if not doc:
        return RedirectResponse('/dashboard', status_code=303)
    
    # Redirect to public URL (Supabase Storage)
    return RedirectResponse(doc['file_path'], status_code=303)

@rt('/view/{doc_id}')
async def get(request, doc_id: str):
    """View document (simple preview)"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse('/login', status_code=303)
    
    documents = await get_user_documents(current_user.id)
    
    # Find document
    doc = next((d for d in documents if d['id'] == doc_id), None)
    if not doc:
        return RedirectResponse('/dashboard', status_code=303)
    
    file_path = Path(doc['file_path'])
    if not file_path.exists():
        return RedirectResponse('/dashboard?error=file_not_found', status_code=303)
    
    # For PDFs, we can embed them
    if doc['mime_type'] == 'application/pdf':
        return Div(
            Div(
                Div(
                    A('← Volver al Dashboard', href='/dashboard', cls='bg-gray-700 hover:bg-gray-800 text-white px-6 py-3 rounded-lg font-semibold transition inline-block mb-6'),
                    H1(f"📄 {doc['filename']}", cls='text-3xl font-bold text-gray-800 mb-6'),
                    Div(
                        Iframe(src=f"/download/{doc_id}", cls='w-full h-screen rounded-xl shadow-2xl border-4 border-gray-200'),
                    ),
                    cls='max-w-7xl mx-auto px-4 py-8'
                ),
                cls='min-h-screen bg-gradient-to-br from-purple-50 via-indigo-50 to-purple-100'
            )
        )
    else:
        # For other files, offer download
        return Div(
            Div(
                Div(
                    A('← Volver al Dashboard', href='/dashboard', cls='bg-gray-700 hover:bg-gray-800 text-white px-6 py-3 rounded-lg font-semibold transition inline-block mb-6'),
                    Div(
                        H1(f"📄 {doc['filename']}", cls='text-3xl font-bold text-gray-800 mb-6'),
                        Div(
                            Div(
                                P('📄', cls='text-6xl text-center mb-4'),
                                P(f"Tipo de archivo: {doc['mime_type']}", cls='text-gray-700 mb-2'),
                                P(f"Tamaño: {doc['file_size'] / 1024:.2f} KB", cls='text-gray-700 mb-4'),
                                P('Este tipo de archivo no se puede previsualizar en el navegador.', cls='text-gray-600 mb-6'),
                                A('📥 Descargar', href=f"/download/{doc_id}", cls='block w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700 text-center transition mb-3'),
                                A('← Volver al Dashboard', href='/dashboard', cls='block w-full bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg font-semibold text-center transition')
                            ),
                            cls='bg-white rounded-2xl shadow-2xl p-8'
                        ),
                        cls='max-w-2xl mx-auto'
                    ),
                    cls='px-4 py-8'
                ),
                cls='min-h-screen bg-gradient-to-br from-purple-50 via-indigo-50 to-purple-100'
            )
        )

# Initialize database on startup
@app.on_event("startup")
async def startup():
    await init_db()

# Serve static files
@rt('/static/{filepath:path}')
def get(filepath: str):
    return FileResponse(f'static/{filepath}')

# Export app for Vercel
handler = app

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
