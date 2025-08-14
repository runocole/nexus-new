from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0003_add_missing_visit_count'),  
    ]
    
    operations = [
        migrations.AddField(
            model_name='product',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
    ]