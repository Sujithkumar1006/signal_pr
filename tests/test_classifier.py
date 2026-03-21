from pr_assistant.classifier import classify_changed_files, classify_file_path
from pr_assistant.github_client import ChangedFile


def test_classify_representative_rails_paths():
    assert classify_file_path("app/models/user.rb").category == "models"
    assert classify_file_path("app/controllers/users_controller.rb").category == "controllers"
    assert classify_file_path("app/views/users/index.html.erb").category == "views"
    assert classify_file_path("app/helpers/users_helper.rb").category == "helpers"
    assert classify_file_path("app/services/review_runner.rb").category == "services"
    assert classify_file_path("app/jobs/sync_job.rb").category == "jobs"
    assert classify_file_path("app/mailers/user_mailer.rb").category == "mailers"
    assert classify_file_path("app/policies/user_policy.rb").category == "policies"
    assert classify_file_path("app/serializers/user_serializer.rb").category == "serializers_presenters"
    assert classify_file_path("app/presenters/user_presenter.rb").category == "serializers_presenters"
    assert classify_file_path("app/components/user_card_component.rb").category == "components"
    assert classify_file_path("app/javascript/controllers/index.js").category == "frontend_assets"
    assert classify_file_path("app/assets/stylesheets/application.css").category == "frontend_assets"


def test_classify_special_config_database_and_dependency_paths():
    assert classify_file_path("config/routes.rb").category == "routes"
    assert classify_file_path("config/initializers/sidekiq.rb").category == "initializers"
    assert classify_file_path("config/environments/production.rb").category == "config"
    assert classify_file_path("db/schema.rb").category == "database_schema"
    assert classify_file_path("db/migrate/20260321_add_reviews.rb").category == "migrations"
    assert classify_file_path("Gemfile").category == "gem_dependencies"
    assert classify_file_path("Gemfile.lock").category == "gem_dependencies"


def test_classify_test_ci_and_documentation_paths():
    assert classify_file_path("spec/services/review_runner_spec.rb").category == "tests"
    assert classify_file_path("test/models/user_test.rb").category == "tests"
    assert classify_file_path(".github/workflows/ci.yml").category == "ci_automation"
    assert classify_file_path("README.md").category == "documentation"
    assert classify_file_path("docs/architecture.md").category == "documentation"


def test_unknown_paths_fall_back_conservatively():
    classification = classify_file_path("lib/tasks/review.rake")

    assert classification.category == "other_rails_adjacent"
    assert classification.confidence == "low"


def test_classify_changed_files_returns_per_path_mapping():
    changed_files = [
        ChangedFile(
            path="app/models/user.rb",
            status="modified",
            additions=10,
            deletions=2,
            patch_available=True,
            patch="@@ -1 +1 @@",
        ),
        ChangedFile(
            path="docs/reviewing.md",
            status="added",
            additions=20,
            deletions=0,
            patch_available=True,
            patch="@@ -0,0 +1,20 @@",
        ),
    ]

    classifications = classify_changed_files(changed_files)

    assert classifications["app/models/user.rb"].category == "models"
    assert classifications["docs/reviewing.md"].category == "documentation"
