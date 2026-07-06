"""RLS policies for NumberSequence and IntegrationTransaction (PLT-1, ADR-0002)."""

from django.db import migrations

from core.db import rls_disable_sql, rls_enable_sql


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_numbering_integrations"),
    ]

    operations = [
        migrations.RunSQL(
            sql=rls_enable_sql("core_numbersequence"),
            reverse_sql=rls_disable_sql("core_numbersequence"),
        ),
        migrations.RunSQL(
            sql=rls_enable_sql("core_integrationtransaction"),
            reverse_sql=rls_disable_sql("core_integrationtransaction"),
        ),
    ]
