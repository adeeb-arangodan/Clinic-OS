import factory

from core.models import Branch, Entitlement, Tenant, User


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Clinic {n}")
    subdomain = factory.Sequence(lambda n: f"clinic{n}")


class BranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Branch

    tenant = factory.SubFactory(TenantFactory)
    name_en = factory.Sequence(lambda n: f"Branch {n}")
    name_ar = factory.Sequence(lambda n: f"فرع {n}")


class EntitlementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Entitlement

    tenant = factory.SubFactory(TenantFactory)
    feature_code = factory.Sequence(lambda n: f"feature_{n}")
    enabled = True


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    tenant = factory.SubFactory(TenantFactory)
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda u: f"{u.username}@example.com")
