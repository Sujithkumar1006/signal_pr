from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationRule:
    category: str
    confidence: str
    rationale: str
    exact: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    regex: str | None = None


CLASSIFICATION_RULES = (
    ClassificationRule(
        category="routes",
        confidence="high",
        rationale="Path matches config/routes.rb",
        exact=("config/routes.rb",),
    ),
    ClassificationRule(
        category="database_schema",
        confidence="high",
        rationale="Path matches db/schema.rb",
        exact=("db/schema.rb",),
    ),
    ClassificationRule(
        category="gem_dependencies",
        confidence="high",
        rationale="Path matches Gemfile or Gemfile.lock",
        exact=("Gemfile", "Gemfile.lock"),
    ),
    ClassificationRule(
        category="documentation",
        confidence="high",
        rationale="Path is a README* file or under docs/",
        prefixes=("docs/",),
        regex=r"^README(?:\..+)?$",
    ),
    ClassificationRule(
        category="models",
        confidence="high",
        rationale="Path is under app/models/",
        prefixes=("app/models/",),
    ),
    ClassificationRule(
        category="controllers",
        confidence="high",
        rationale="Path is under app/controllers/",
        prefixes=("app/controllers/",),
    ),
    ClassificationRule(
        category="views",
        confidence="high",
        rationale="Path is under app/views/",
        prefixes=("app/views/",),
    ),
    ClassificationRule(
        category="helpers",
        confidence="high",
        rationale="Path is under app/helpers/",
        prefixes=("app/helpers/",),
    ),
    ClassificationRule(
        category="services",
        confidence="high",
        rationale="Path is under app/services/",
        prefixes=("app/services/",),
    ),
    ClassificationRule(
        category="jobs",
        confidence="high",
        rationale="Path is under app/jobs/",
        prefixes=("app/jobs/",),
    ),
    ClassificationRule(
        category="mailers",
        confidence="high",
        rationale="Path is under app/mailers/",
        prefixes=("app/mailers/",),
    ),
    ClassificationRule(
        category="policies",
        confidence="high",
        rationale="Path is under app/policies/",
        prefixes=("app/policies/",),
    ),
    ClassificationRule(
        category="serializers_presenters",
        confidence="high",
        rationale="Path is under app/serializers/ or app/presenters/",
        prefixes=("app/serializers/", "app/presenters/"),
    ),
    ClassificationRule(
        category="components",
        confidence="high",
        rationale="Path is under app/components/",
        prefixes=("app/components/",),
    ),
    ClassificationRule(
        category="frontend_assets",
        confidence="high",
        rationale="Path is under app/javascript/ or app/assets/",
        prefixes=("app/javascript/", "app/assets/"),
    ),
    ClassificationRule(
        category="migrations",
        confidence="high",
        rationale="Path is under db/migrate/",
        prefixes=("db/migrate/",),
    ),
    ClassificationRule(
        category="tests",
        confidence="high",
        rationale="Path is under spec/ or test/",
        prefixes=("spec/", "test/"),
    ),
    ClassificationRule(
        category="initializers",
        confidence="high",
        rationale="Path is under config/initializers/",
        prefixes=("config/initializers/",),
    ),
    ClassificationRule(
        category="ci_automation",
        confidence="high",
        rationale="Path is under .github/workflows/",
        prefixes=(".github/workflows/",),
    ),
    ClassificationRule(
        category="config",
        confidence="medium",
        rationale="Path is under config/",
        prefixes=("config/",),
    ),
)
