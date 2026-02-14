# Playbook - Cifrado de credenciales Dropi

## Objetivo

Operar el cifrado reversible de `dropi_password` con una clave dedicada (`DROPI_PASSWORD_ENCRYPTION_KEY`) y reducir riesgo durante despliegues y rollback.

## Reglas obligatorias

- `DROPI_PASSWORD_ENCRYPTION_KEY` es obligatoria en producción.
- No reutilizar `SECRET_KEY` para cifrado de credenciales Dropi.
- No rotar `DROPI_PASSWORD_ENCRYPTION_KEY` sin plan de re-cifrado.

## Antes de desplegar migración 0018

1. Definir `DROPI_PASSWORD_ENCRYPTION_KEY` en `.env.production`.
2. Verificar backup de base de datos:
   - `docker compose exec db pg_dump -U droptools_admin -d droptools_db > backup_pre_0018.sql`
3. Verificar que el backend arranca con esa clave en un entorno staging.

## Despliegue recomendado (sin downtime)

1. Subir variables de entorno nuevas.
2. Desplegar código.
3. Ejecutar migración:
   - `docker compose exec backend python backend/manage.py migrate`
4. Validar flujo de reporter para al menos un usuario real:
   - Guardar credenciales Dropi.
   - Leer credenciales y ejecutar inicio de reporter.

## Rotación de clave (procedimiento seguro)

No cambiar la clave directamente en caliente. Hacer:

1. Backup completo de DB.
2. Ventana controlada.
3. Script de re-cifrado:
   - Descifrar con clave actual.
   - Cifrar con clave nueva.
4. Actualizar `.env.production` con clave nueva.
5. Validar lectura de credenciales para varios usuarios.

## Rollback

Si la aplicación falla después de migrar:

1. Mantener la misma `DROPI_PASSWORD_ENCRYPTION_KEY` usada al migrar.
2. Revertir release de aplicación si aplica.
3. Si hay corrupción o pérdida de legibilidad:
   - Restaurar base de datos desde `backup_pre_0018.sql`.
4. No ejecutar rollback de migración con una clave distinta.

