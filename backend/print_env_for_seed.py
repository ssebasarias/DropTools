import os


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dahell_backend.settings")
    import django  # noqa: WPS433

    django.setup()

    # After django-environ reads .env, these should be present in os.environ
    keys = [
        "DROPI_EMAIL",
        "DROPI_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "DEBUG",
    ]

    for k in keys:
        v = os.getenv(k)
        if k.lower().endswith("password"):
            print(f"{k} set: {bool(v)}")
        else:
            print(f"{k}={v}")


if __name__ == "__main__":
    main()

