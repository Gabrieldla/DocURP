import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", SUPABASE_ANON_KEY)

# Create Supabase client with service role for admin operations
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def init_db():
    """Initialize database - Supabase Auth handles user management"""
    print("✅ Supabase Auth configurado. Los usuarios se gestionan automáticamente.")
    print("📧 Asegúrate de configurar los templates de email en el dashboard de Supabase.")
    print("🔧 Ve a: Authentication > Email Templates")

async def signup_user(email: str, password: str, name: str, student_code: str):
    """Sign up user with Supabase Auth - trigger creates profile automatically"""
    try:
        # Create auth user - the trigger will create the profile automatically
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name,
                    "student_code": student_code
                }
            }
        })
        
        if auth_response.user:
            return {
                'user': auth_response.user,
                'session': auth_response.session
            }
        return None
    except Exception as e:
        print(f"❌ Error signing up user: {e}")
        return None

async def signin_user(email: str, password: str):
    """Sign in user with Supabase Auth"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response
    except Exception as e:
        print(f"❌ Error signing in: {e}")
        return None

async def reset_password_email(email: str, redirect_to: str = None):
    """Send password reset email"""
    try:
        options = {"redirect_to": redirect_to} if redirect_to else {}
        response = supabase.auth.reset_password_for_email(email, options)
        print(f"✅ Reset email sent to {email} with redirect: {redirect_to}")
        return response
    except Exception as e:
        print(f"❌ Error sending reset email: {e}")
        import traceback
        traceback.print_exc()
        return None

async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    try:
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting profile: {e}")
        return None

async def get_profile_by_email(email: str):
    """Get profile by email"""
    try:
        response = supabase.table('profiles').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting profile by email: {e}")
        return None

async def get_profile_by_student_code(student_code: str):
    """Get profile by student code"""
    try:
        response = supabase.table('profiles').select('*').eq('student_code', student_code).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting profile by student code: {e}")
        return None

async def save_document(user_id: str, filename: str, stored_filename: str, 
                       file_path: str, file_size: int, mime_type: str, description: str = None):
    """Save document metadata"""
    try:
        response = supabase.table('documents').insert({
            'user_id': user_id,
            'filename': filename,
            'stored_filename': stored_filename,
            'file_path': file_path,
            'file_size': file_size,
            'mime_type': mime_type,
            'description': description
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving document: {e}")
        return None

async def get_user_documents(user_id: str):
    """Get all documents for a user"""
    try:
        response = supabase.table('documents').select('*').eq('user_id', user_id).order('uploaded_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting documents: {e}")
        return []

async def delete_document(doc_id: str):
    """Delete a document"""
    try:
        supabase.table('documents').delete().eq('id', doc_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting document: {e}")
        return False
