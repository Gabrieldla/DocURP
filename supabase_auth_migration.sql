-- Migration to Supabase Auth
-- Ejecuta este SQL en el SQL Editor de Supabase

-- 0. LIMPIAR TODO PRIMERO
-- Eliminar funciones y triggers
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;

-- Eliminar constraints problemáticas
ALTER TABLE IF EXISTS profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey CASCADE;

-- Eliminar tablas en orden correcto (por dependencias)
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Crear tabla de perfiles (profiles) vinculada a auth.users
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    student_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- 2. Crear tabla documents vinculada a auth.users
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    description TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- 3. Crear índices
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_student_code ON profiles(student_code);

-- 4. Habilitar RLS
-- Profiles no necesita RLS porque solo se accede via backend con service role
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- 5. Eliminar políticas existentes (si existen)
DROP POLICY IF EXISTS "Users can view own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON documents;

-- 6. Políticas RLS para profiles
-- No se crean políticas porque RLS está deshabilitado en profiles
-- El acceso se controla via service role key en el backend

-- 7. Políticas RLS para documents
CREATE POLICY "Users can view own documents" ON documents
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents" ON documents
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents" ON documents
    FOR DELETE
    USING (auth.uid() = user_id);

-- 8. Función trigger para crear perfil automáticamente
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, name, student_code)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'name', 'Usuario'),
        COALESCE(NEW.raw_user_meta_data->>'student_code', '000000000')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 9. Crear trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 10. Configuración de Email (importante)
-- Ve a: Authentication > Email Templates en el dashboard
-- Personaliza los templates de:
-- - Confirm signup
-- - Magic Link
-- - Change Email Address
-- - Reset Password
