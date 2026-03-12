# Generated manually for populate_user_collection skip-by-entry-id (idempotent for prod-copy DBs)

from django.db import connection, migrations, models


def add_id_fka_entry_if_missing(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'collection_baseitem'
            AND column_name = 'id_fka_entry'
            """
        )
        if cursor.fetchone():
            return
    schema_editor.execute(
        "ALTER TABLE collection_baseitem ADD COLUMN id_fka_entry integer NULL;"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS baseitem_user_id_fka_entry_idx "
        "ON collection_baseitem (user_id, id_fka_entry);"
    )


def reverse_add_id_fka_entry(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'collection_baseitem'
            AND column_name = 'id_fka_entry'
            """
        )
        if not cursor.fetchone():
            return
    schema_editor.execute("DROP INDEX IF EXISTS baseitem_user_id_fka_entry_idx;")
    schema_editor.execute("ALTER TABLE collection_baseitem DROP COLUMN IF EXISTS id_fka_entry;")


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0002_add_performance_indexes"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="baseitem",
                    name="id_fka_entry",
                    field=models.PositiveIntegerField(
                        blank=True,
                        db_index=True,
                        help_text="FootballKitArchive user-collection entry id; used to skip duplicates on re-import.",
                        null=True,
                    ),
                ),
                migrations.AddIndex(
                    model_name="baseitem",
                    index=models.Index(
                        fields=["user", "id_fka_entry"], name="baseitem_user_id_fka_entry_idx"
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_id_fka_entry_if_missing, reverse_add_id_fka_entry),
            ],
        ),
    ]
