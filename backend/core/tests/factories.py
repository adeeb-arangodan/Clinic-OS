import factory

from core.models import Branch, Entitlement, Role, Tenant, User, UserRole


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
    password = factory.django.Password("correct-horse-9!")


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role

    tenant = factory.SubFactory(TenantFactory)
    name_en = factory.Sequence(lambda n: f"Role {n}")
    name_ar = factory.Sequence(lambda n: f"دور {n}")
    permissions = factory.LazyFunction(list)


class UserRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRole

    tenant = factory.SubFactory(TenantFactory)
    user = factory.SubFactory(UserFactory, tenant=factory.SelfAttribute("..tenant"))
    role = factory.SubFactory(RoleFactory, tenant=factory.SelfAttribute("..tenant"))
