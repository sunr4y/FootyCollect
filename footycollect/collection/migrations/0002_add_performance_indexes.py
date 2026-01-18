# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='baseitem',
            index=models.Index(fields=['user', 'item_type'], name='baseitem_user_item_type_idx'),
        ),
        migrations.AddIndex(
            model_name='baseitem',
            index=models.Index(fields=['user', 'is_private', 'is_draft'], name='baseitem_user_visibility_idx'),
        ),
        migrations.AddIndex(
            model_name='baseitem',
            index=models.Index(fields=['user', 'created_at'], name='baseitem_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='baseitem',
            index=models.Index(fields=['club', 'season'], name='baseitem_club_season_idx'),
        ),
        migrations.AddIndex(
            model_name='jersey',
            index=models.Index(fields=['size'], name='jersey_size_idx'),
        ),
        migrations.AddIndex(
            model_name='jersey',
            index=models.Index(fields=['kit'], name='jersey_kit_idx'),
        ),
    ]
