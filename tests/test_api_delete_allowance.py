import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from ..views_api_minimal import allowance_api_router
from ..models import Allowance


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(allowance_api_router)
    return TestClient(app)


@pytest.fixture
def mock_wallet():
    wallet = AsyncMock()
    wallet.wallet.id = "test_wallet_id"
    return wallet


@pytest.fixture
def mock_allowance():
    return Allowance(
        id="test_allowance_id",
        name="Test Allowance",
        wallet="test_wallet_id",
        lightning_address="test@example.com",
        amount=1000,
        currency="sats",
        start_date=datetime(2024, 1, 1),
        frequency_type="daily",
        next_payment_date=datetime(2024, 1, 2),
        memo="Test memo",
        active=True
    )


class TestDeleteAllowanceAPI:
    
    @patch('..views_api_minimal.delete_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_success(self, mock_require_admin_key, mock_get_allowance, mock_delete_allowance, client, mock_wallet, mock_allowance):
        """Test successful deletion of allowance"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_delete_allowance.return_value = None
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions - The minimal API returns a JSON message, not 204
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Allowance deleted"
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test_allowance_id")
        mock_delete_allowance.assert_called_once_with("test_allowance_id")
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_not_found(self, mock_require_admin_key, mock_get_allowance, client, mock_wallet):
        """Test deleting allowance that doesn't exist"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = None
        
        # Make request
        response = client.delete("/api/v1/allowance/nonexistent_id")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Allowance does not exist."
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("nonexistent_id")
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_wrong_wallet(self, mock_require_admin_key, mock_get_allowance, client, mock_allowance):
        """Test deleting allowance from different wallet (forbidden)"""
        # Setup mocks - different wallet ID
        wrong_wallet = AsyncMock()
        wrong_wallet.wallet.id = "different_wallet_id"
        
        mock_require_admin_key.return_value = wrong_wallet
        mock_get_allowance.return_value = mock_allowance  # Has wallet "test_wallet_id"
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Not your allowance."
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test_allowance_id")
    
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_invalid_admin_key(self, mock_require_admin_key, client):
        """Test deleting allowance with invalid admin key"""
        # Setup mocks to raise authentication error
        mock_require_admin_key.side_effect = HTTPException(status_code=403, detail="Admin key required")
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 403
    
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_empty_id(self, mock_require_admin_key, client, mock_wallet):
        """Test deleting allowance with empty ID"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Make request with empty ID
        response = client.delete("/api/v1/allowance/")
        
        # Assertions - should return 404 for malformed URL
        assert response.status_code == 404
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_database_error_on_get(self, mock_require_admin_key, mock_get_allowance, client, mock_wallet):
        """Test deleting allowance when database error occurs during get"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 500
    
    @patch('..views_api_minimal.delete_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_database_error_on_delete(self, mock_require_admin_key, mock_get_allowance, mock_delete_allowance, client, mock_wallet, mock_allowance):
        """Test deleting allowance when database error occurs during delete"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_delete_allowance.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 500
    
    @patch('..views_api_minimal.delete_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_special_characters(self, mock_require_admin_key, mock_get_allowance, mock_delete_allowance, client, mock_wallet, mock_allowance):
        """Test deleting allowance with special characters in ID"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_allowance.id = "test-allowance_123"
        mock_get_allowance.return_value = mock_allowance
        mock_delete_allowance.return_value = None
        
        # Make request
        response = client.delete("/api/v1/allowance/test-allowance_123")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Allowance deleted"
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test-allowance_123")
        mock_delete_allowance.assert_called_once_with("test-allowance_123")
    
    @patch('..views_api_minimal.delete_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_delete_allowance_wallet_permission_check(self, mock_require_admin_key, mock_get_allowance, mock_delete_allowance, client, mock_wallet, mock_allowance):
        """Test that wallet permission is properly checked before deletion"""
        # Setup mocks - same wallet ID
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_delete_allowance.return_value = None
        
        # Verify allowance wallet matches admin wallet
        assert mock_allowance.wallet == mock_wallet.wallet.id
        
        # Make request
        response = client.delete("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Allowance deleted"
        
        # Verify that get_allowance was called to check permissions
        mock_get_allowance.assert_called_once_with("test_allowance_id")
        mock_delete_allowance.assert_called_once_with("test_allowance_id")