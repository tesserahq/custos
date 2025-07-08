"""
Tests for Template API Endpoints
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, MagicMock


class TestTemplateEndpoints:
    """Test cases for template API endpoints."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary templates directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch the templates directory in the service
            from app.services.role_template_service import role_template_service

            with patch.object(role_template_service, "templates_dir", temp_dir):
                yield temp_dir

    @pytest.fixture
    def sample_role_config(self):
        """Sample role configuration for testing."""
        return {
            "roles": {
                "admin": {
                    "description": "Full system administrator",
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "documents": ["read", "write", "delete", "create"],
                    },
                },
                "editor": {
                    "description": "Content editor",
                    "permissions": {
                        "users": ["read"],
                        "documents": ["read", "write", "create"],
                    },
                },
            }
        }

    def test_create_role_template_success(
        self, client, temp_templates_dir, sample_role_config
    ):
        """Test successful template creation."""
        request_data = {
            "template_name": "test-template",
            "role_config": sample_role_config,
        }

        with patch(
            "app.services.role_template_service.role_template_service.create_role_template"
        ) as mock_create:
            mock_create.return_value = True

            response = client.post("/authorization/templates", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["template_name"] == "test-template"
            assert "created successfully" in data["message"]

            mock_create.assert_called_once_with("test-template", sample_role_config)

    def test_create_role_template_missing_fields(self, client):
        """Test template creation with missing fields."""
        # Missing template_name
        request_data = {"role_config": {"roles": {}}}

        response = client.post("/authorization/templates", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "template_name and role_config are required" in data["detail"]

        # Missing role_config
        request_data = {"template_name": "test-template"}

        response = client.post("/authorization/templates", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "template_name and role_config are required" in data["detail"]

    def test_create_role_template_service_failure(self, client, sample_role_config):
        """Test template creation when service fails."""
        request_data = {
            "template_name": "test-template",
            "role_config": sample_role_config,
        }

        with patch(
            "app.services.role_template_service.role_template_service.create_role_template"
        ) as mock_create:
            mock_create.return_value = False

            response = client.post("/authorization/templates", json=request_data)

            assert response.status_code == 500
            data = response.json()
            assert "Failed to create template" in data["detail"]

    def test_list_role_templates_success(self, client):
        """Test successful template listing."""
        with patch(
            "app.services.role_template_service.role_template_service.list_role_templates"
        ) as mock_list:
            mock_list.return_value = ["template-1", "template-2", "template-3"]

            response = client.get("/authorization/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["templates"] == ["template-1", "template-2", "template-3"]
            assert data["count"] == 3

    def test_list_role_templates_empty(self, client):
        """Test template listing when no templates exist."""
        with patch(
            "app.services.role_template_service.role_template_service.list_role_templates"
        ) as mock_list:
            mock_list.return_value = []

            response = client.get("/authorization/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["templates"] == []
            assert data["count"] == 0

    def test_get_role_template_success(self, client, sample_role_config):
        """Test successful template retrieval."""
        with patch(
            "app.services.role_template_service.role_template_service.get_role_template"
        ) as mock_get:
            mock_get.return_value = sample_role_config

            response = client.get("/authorization/templates/test-template")

            assert response.status_code == 200
            data = response.json()
            assert data["template_name"] == "test-template"
            assert data["config"] == sample_role_config

    def test_get_role_template_not_found(self, client):
        """Test template retrieval when template doesn't exist."""
        with patch(
            "app.services.role_template_service.role_template_service.get_role_template"
        ) as mock_get:
            mock_get.return_value = None

            response = client.get("/authorization/templates/non-existent-template")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]

    def test_apply_template_to_domain_success(self, client):
        """Test successful template application to domain."""
        request_data = {"domain": "test-domain", "overwrite_existing": True}

        expected_results = {"admin": True, "editor": True}

        with patch(
            "app.services.role_template_service.role_template_service.apply_template_to_domain"
        ) as mock_apply:
            mock_apply.return_value = expected_results

            response = client.post(
                "/authorization/templates/test-template/apply", json=request_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["template_name"] == "test-template"
            assert data["domain"] == "test-domain"
            assert data["results"] == expected_results
            assert data["success"] is True

            mock_apply.assert_called_once_with("test-template", "test-domain", True)

    def test_apply_template_to_domain_missing_domain(self, client):
        """Test template application with missing domain."""
        request_data = {"overwrite_existing": True}

        response = client.post(
            "/authorization/templates/test-template/apply", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "domain is required" in data["detail"]

    def test_apply_template_to_domain_service_error(self, client):
        """Test template application when service returns error."""
        request_data = {"domain": "test-domain", "overwrite_existing": True}

        with patch(
            "app.services.role_template_service.role_template_service.apply_template_to_domain"
        ) as mock_apply:
            mock_apply.return_value = {"error": "Template not found"}

            response = client.post(
                "/authorization/templates/test-template/apply", json=request_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_apply_template_to_multiple_domains_success(self, client):
        """Test successful template application to multiple domains."""
        request_data = {
            "domains": ["domain-1", "domain-2", "domain-3"],
            "overwrite_existing": False,
        }

        expected_results = {
            "domain-1": {"admin": True, "editor": True},
            "domain-2": {"admin": True, "editor": True},
            "domain-3": {"admin": True, "editor": True},
        }

        with patch(
            "app.services.role_template_service.role_template_service.apply_template_to_multiple_domains"
        ) as mock_apply:
            mock_apply.return_value = expected_results

            response = client.post(
                "/authorization/templates/test-template/apply-multiple",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["template_name"] == "test-template"
            assert data["domains"] == ["domain-1", "domain-2", "domain-3"]
            assert data["results"] == expected_results
            assert data["success_count"] == 3
            assert data["total_domains"] == 3

            mock_apply.assert_called_once_with(
                "test-template", ["domain-1", "domain-2", "domain-3"], False
            )

    def test_apply_template_to_multiple_domains_missing_domains(self, client):
        """Test template application with missing domains list."""
        request_data = {"overwrite_existing": True}

        response = client.post(
            "/authorization/templates/test-template/apply-multiple", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "domains list is required" in data["detail"]

    def test_apply_template_to_multiple_domains_partial_success(self, client):
        """Test template application with partial success."""
        request_data = {
            "domains": ["domain-1", "domain-2", "domain-3"],
            "overwrite_existing": True,
        }

        expected_results = {
            "domain-1": {"admin": True, "editor": True},
            "domain-2": {"error": "Domain not found"},
            "domain-3": {"admin": True, "editor": True},
        }

        with patch(
            "app.services.role_template_service.role_template_service.apply_template_to_multiple_domains"
        ) as mock_apply:
            mock_apply.return_value = expected_results

            response = client.post(
                "/authorization/templates/test-template/apply-multiple",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 2  # Only 2 successful domains
            assert data["total_domains"] == 3

    def test_add_permission_to_template_success(self, client):
        """Test successful permission addition to template."""
        request_data = {"role_name": "admin", "resource": "reports", "action": "export"}

        with patch(
            "app.services.role_template_service.role_template_service.add_permission_to_template"
        ) as mock_add:
            mock_add.return_value = True

            response = client.post(
                "/authorization/templates/test-template/add-permission",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["template_name"] == "test-template"
            assert data["role_name"] == "admin"
            assert data["resource"] == "reports"
            assert data["action"] == "export"
            assert "Permission export:reports added to role admin" in data["message"]

            mock_add.assert_called_once_with(
                "test-template", "admin", "reports", "export"
            )

    def test_add_permission_to_template_missing_fields(self, client):
        """Test permission addition with missing fields."""
        # Missing role_name
        request_data = {"resource": "reports", "action": "export"}

        response = client.post(
            "/authorization/templates/test-template/add-permission", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "role_name, resource, and action are required" in data["detail"]

        # Missing resource
        request_data = {"role_name": "admin", "action": "export"}

        response = client.post(
            "/authorization/templates/test-template/add-permission", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "role_name, resource, and action are required" in data["detail"]

        # Missing action
        request_data = {"role_name": "admin", "resource": "reports"}

        response = client.post(
            "/authorization/templates/test-template/add-permission", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "role_name, resource, and action are required" in data["detail"]

    def test_add_permission_to_template_service_failure(self, client):
        """Test permission addition when service fails."""
        request_data = {"role_name": "admin", "resource": "reports", "action": "export"}

        with patch(
            "app.services.role_template_service.role_template_service.add_permission_to_template"
        ) as mock_add:
            mock_add.return_value = False

            response = client.post(
                "/authorization/templates/test-template/add-permission",
                json=request_data,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Failed to add permission to template" in data["detail"]

    def test_remove_permission_from_template_success(self, client):
        """Test successful permission removal from template."""
        request_data = {"role_name": "admin", "resource": "reports", "action": "export"}

        with patch(
            "app.services.role_template_service.role_template_service.remove_permission_from_template"
        ) as mock_remove:
            mock_remove.return_value = True

            response = client.post(
                "/authorization/templates/test-template/remove-permission",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["template_name"] == "test-template"
            assert data["role_name"] == "admin"
            assert data["resource"] == "reports"
            assert data["action"] == "export"
            assert (
                "Permission export:reports removed from role admin" in data["message"]
            )

            mock_remove.assert_called_once_with(
                "test-template", "admin", "reports", "export"
            )

    def test_remove_permission_from_template_service_failure(self, client):
        """Test permission removal when service fails."""
        request_data = {"role_name": "admin", "resource": "reports", "action": "export"}

        with patch(
            "app.services.role_template_service.role_template_service.remove_permission_from_template"
        ) as mock_remove:
            mock_remove.return_value = False

            response = client.post(
                "/authorization/templates/test-template/remove-permission",
                json=request_data,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Failed to remove permission from template" in data["detail"]

    def test_update_template_and_apply_success(self, client, sample_role_config):
        """Test successful template update and application."""
        request_data = {
            "updated_config": sample_role_config,
            "domains": ["domain-1", "domain-2", "domain-3"],
            "overwrite_existing": True,
        }

        expected_results = {
            "domain-1": {"admin": True, "editor": True},
            "domain-2": {"admin": True, "editor": True},
            "domain-3": {"admin": True, "editor": True},
        }

        with patch(
            "app.services.role_template_service.role_template_service.update_template_and_apply"
        ) as mock_update:
            mock_update.return_value = expected_results

            response = client.post(
                "/authorization/templates/test-template/update-and-apply",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["template_name"] == "test-template"
            assert data["domains"] == ["domain-1", "domain-2", "domain-3"]
            assert data["results"] == expected_results
            assert data["success_count"] == 3
            assert data["total_domains"] == 3
            assert "Template updated and applied to 3/3 domains" in data["message"]

            mock_update.assert_called_once_with(
                "test-template",
                sample_role_config,
                ["domain-1", "domain-2", "domain-3"],
                True,
            )

    def test_update_template_and_apply_missing_fields(self, client):
        """Test template update and application with missing fields."""
        # Missing updated_config
        request_data = {"domains": ["domain-1", "domain-2"]}

        response = client.post(
            "/authorization/templates/test-template/update-and-apply", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "updated_config and domains are required" in data["detail"]

        # Missing domains
        request_data = {"updated_config": {"roles": {}}}

        response = client.post(
            "/authorization/templates/test-template/update-and-apply", json=request_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "updated_config and domains are required" in data["detail"]

    def test_update_template_and_apply_service_failure(
        self, client, sample_role_config
    ):
        """Test template update and application when service fails."""
        request_data = {
            "updated_config": sample_role_config,
            "domains": ["domain-1", "domain-2"],
            "overwrite_existing": True,
        }

        with patch(
            "app.services.role_template_service.role_template_service.update_template_and_apply"
        ) as mock_update:
            # Return error for each domain
            mock_update.return_value = {
                "domain-1": {"error": "Failed to update template"},
                "domain-2": {"error": "Failed to update template"},
            }

            response = client.post(
                "/authorization/templates/test-template/update-and-apply",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 0
            assert data["total_domains"] == 2
            assert "Template updated and applied to 0/2 domains" in data["message"]

    def test_endpoint_error_handling(self, client):
        """Test error handling in endpoints."""
        # Test with invalid JSON
        response = client.post("/authorization/templates", data="invalid json")

        assert response.status_code == 422  # Validation error

    def test_template_endpoints_integration(
        self, client, temp_templates_dir, sample_role_config
    ):
        """Test integration between template endpoints."""
        # 1. Create template
        create_data = {
            "template_name": "integration-test",
            "role_config": sample_role_config,
        }

        with patch(
            "app.services.role_template_service.role_template_service.create_role_template"
        ) as mock_create:
            mock_create.return_value = True

            response = client.post("/authorization/templates", json=create_data)
            assert response.status_code == 200

        # 2. List templates
        with patch(
            "app.services.role_template_service.role_template_service.list_role_templates"
        ) as mock_list:
            mock_list.return_value = ["integration-test"]

            response = client.get("/authorization/templates")
            assert response.status_code == 200
            data = response.json()
            assert "integration-test" in data["templates"]

        # 3. Get template
        with patch(
            "app.services.role_template_service.role_template_service.get_role_template"
        ) as mock_get:
            mock_get.return_value = sample_role_config

            response = client.get("/authorization/templates/integration-test")
            assert response.status_code == 200
            data = response.json()
            assert data["config"] == sample_role_config

        # 4. Add permission
        add_permission_data = {
            "role_name": "admin",
            "resource": "analytics",
            "action": "dashboard",
        }

        with patch(
            "app.services.role_template_service.role_template_service.add_permission_to_template"
        ) as mock_add:
            mock_add.return_value = True

            response = client.post(
                "/authorization/templates/integration-test/add-permission",
                json=add_permission_data,
            )
            assert response.status_code == 200

        # 5. Apply to domains
        apply_data = {
            "domains": ["test-domain-1", "test-domain-2"],
            "overwrite_existing": True,
        }

        with patch(
            "app.services.role_template_service.role_template_service.apply_template_to_multiple_domains"
        ) as mock_apply:
            mock_apply.return_value = {
                "test-domain-1": {"admin": True, "editor": True},
                "test-domain-2": {"admin": True, "editor": True},
            }

            response = client.post(
                "/authorization/templates/integration-test/apply-multiple",
                json=apply_data,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 2
