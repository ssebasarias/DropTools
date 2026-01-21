import os


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dahell_backend.settings")
    import django  # noqa: WPS433

    django.setup()

    from django.db import connection  # noqa: WPS433

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user_profiles'
            ORDER BY ordinal_position
            """
        )
        rows = cur.fetchall()

    print("user_profiles columns:")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()

