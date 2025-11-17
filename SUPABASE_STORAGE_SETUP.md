# Configuración de Supabase Storage para DocHub URP

## Paso 1: Crear el bucket

1. Ve a tu proyecto en Supabase Dashboard
2. Click en **Storage** en el menú lateral
3. Click en **"New bucket"**
4. Nombre del bucket: `documents`
5. Selecciona **Public bucket** (para que los usuarios puedan descargar sus archivos)
6. Click en **"Create bucket"**

## Paso 2: Configurar políticas de seguridad (RLS)

Ejecuta este SQL en el SQL Editor de Supabase:

```sql
-- Política para permitir que los usuarios suban archivos a su carpeta
CREATE POLICY "Users can upload to own folder"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Política para permitir que los usuarios vean sus propios archivos
CREATE POLICY "Users can view own files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Política para permitir que los usuarios eliminen sus propios archivos
CREATE POLICY "Users can delete own files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);
```

## Paso 3: Variables de entorno en Vercel

Asegúrate de tener estas variables configuradas en Vercel:

- `SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`

## Paso 4: Deploy

Una vez configurado el bucket y las políticas, haz redeploy en Vercel.

Los archivos ahora se guardarán en Supabase Storage en lugar del disco local.
