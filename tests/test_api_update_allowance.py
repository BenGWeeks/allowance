import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from ..views_api_minimal import allowance_api_router
from ..models import CreateAllowanceData, Allowance


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


@pytest.fixture
def update_data():
    return {
        "name": "Updated Allowance",
        "lightning_address": "updated@example.com",
        "amount": 2000,
        "currency": "sats",
        "start_date": "2024-02-01T00:00:00",
        "frequency_type": "weekly",
        "next_payment_date": "2024-02-08T00:00:00",
        "memo": "Updated memo",
        "active": False
    }


@pytest.fixture
def mock_updated_allowance():
    return Allowance(
        id="test_allowance_id",
        name="Updated Allowance",
        wallet="test_wallet_id",
        lightning_address="updated@example.com",
        amount=2000,
        currency="sats",
        start_date=datetime(2024, 2, 1),
        frequency_type="weekly",
        next_payment_date=datetime(2024, 2, 8),
        memo="Updated memo",
        active=False
    )


class TestUpdateAllowanceAPI:
    
    @patch('..views_api_minimal.update_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_success(self, mock_require_admin_key, mock_get_allowance, mock_update_allowance, client, mock_wallet, mock_allowance, update_data, mock_updated_allowance):
        """Test successful update of allowance"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_update_allowance.return_value = mock_updated_allowance
        
        # Make request
        response = client.put("/api/v1/allowance/test_allowance_id", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Allowance"
        assert data["amount"] == 2000
        assert data["lightning_address"] == "updated@example.com"
        assert data["active"] is False
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test_allowance_id")
        mock_update_allowance.assert_called_once()
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_not_found(self, mock_require_admin_key, mock_get_allowance, client, mock_wallet, update_data):
        """Test updating allowance that doesn't exist"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = None
        
        # Make request
        response = client.put("/api/v1/allowance/nonexistent_id", json=update_data)
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Allowance does not exist."
    
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_empty_id(self, mock_require_admin_key, client, mock_wallet, update_data):
        """Test updating allowance with empty ID"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Make request - empty ID should cause 404
        response = client.put("/api/v1/allowance/", json=update_data)
        
        # Assertions
        assert response.status_code == 404
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_wrong_wallet(self, mock_require_admin_key, mock_get_allowance, client, mock_allowance, update_data):
        """Test updating allowance from different wallet (forbidden)"""
        # Setup mocks - different wallet ID
        wrong_wallet = AsyncMock()
        wrong_wallet.wallet.id = "different_wallet_id"
        
        mock_require_admin_key.return_value = wrong_wallet
        mock_get_allowance.return_value = mock_allowance  # Has wallet "test_wallet_id"
        
        # Make request
        response = client.put("/api/v1/allowance/test_allowance_id", json=update_data)
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Not your allowance."
    
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_invalid_key(self, mock_require_admin_key, client, update_data):
        """Test updating allowance with invalid API key"""
        # Setup mocks to raise authentication error
        mock_require_admin_key.side_effect = HTTPException(status_code=401, detail="Invalid key")
        
        # Make request
        response = client.put("/api/v1/allowance/test_allowance_id", json=update_data)
        
        # Assertions
        assert response.status_code == 401
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_invalid_data(self, mock_require_admin_key, mock_get_allowance, client, mock_wallet, mock_allowance):
        """Test updating allowance with invalid data"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        
        # Test invalid amount
        invalid_data = {
            "name": "Updated Allowance",
            "lightning_address": "updated@example.com",
            "amount": -100,  # Invalid negative amount
            "currency": "sats",
            "start_date": "2024-02-01T00:00:00",
            "frequency_type": "weekly",
            "next_payment_date": "2024-02-08T00:00:00",
            "memo": "Updated memo",
            "active": False
        }
        
        response = client.put("/api/v1/allowance/test_allowance_id", json=invalid_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_missing_required_fields(self, mock_require_admin_key, mock_get_allowance, client, mock_wallet, mock_allowance):
        """Test updating allowance with missing required fields"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        
        # Test missing name
        invalid_data = {
            "lightning_address": "updated@example.com",
            "amount": 2000,
            "currency": "sats",
            "start_date": "2024-02-01T00:00:00",
            "frequency_type": "weekly",
            "next_payment_date": "2024-02-08T00:00:00",
            "memo": "Updated memo",
            "active": False
        }
        
        response = client.put("/api/v1/allowance/test_allowance_id", json=invalid_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.update_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_database_error(self, mock_require_admin_key, mock_get_allowance, mock_update_allowance, client, mock_wallet, mock_allowance, update_data):
        """Test updating allowance when database error occurs"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_update_allowance.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.put("/api/v1/allowance/test_allowance_id", json=update_data)
        
        # Assertions
        assert response.status_code == 500
    
    @patch('..views_api_minimal.update_allowance')
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_update_allowance_partial_data(self, mock_require_admin_key, mock_get_allowance, mock_update_allowance, client, mock_wallet, mock_allowance, mock_updated_allowance):
        """Test updating allowance with partial data"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        mock_update_allowance.return_value = mock_updated_allowance
        
        # Partial update data - only name and amount
        partial_data = {
            "name": "Partially Updated",
            "lightning_address": "test@example.com",
            "amount": 1500,
            "currency": "sats", 
            "start_date": "2024-01-01T00:00:00",
            "frequency_type": "daily",
            "next_payment_date": "2024-01-02T00:00:00",
            "memo": "Test memo",
            "active": True
        }
        
        # Make request
        response = client.put("/api/v1/allowance/test_allowance_id", json=partial_data)
        
        # Assertions
        assert response.status_code == 200