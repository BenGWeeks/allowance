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
def valid_allowance_data():
    return {
        "name": "Test Allowance",
        "lightning_address": "test@example.com",
        "amount": 1000,
        "currency": "sats",
        "start_date": "2024-01-01T00:00:00",
        "frequency_type": "daily",
        "next_payment_date": "2024-01-02T00:00:00",
        "memo": "Test memo",
        "active": True
    }


@pytest.fixture
def mock_created_allowance():
    return Allowance(
        id="new_allowance_id",
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


class TestCreateAllowanceAPI:
    
    @patch('..views_api_minimal.create_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_success(self, mock_require_admin_key, mock_create_allowance, client, mock_wallet, valid_allowance_data, mock_created_allowance):
        """Test successful creation of allowance"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_create_allowance.return_value = mock_created_allowance
        
        # Make request
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new_allowance_id"
        assert data["name"] == "Test Allowance"
        assert data["wallet"] == "test_wallet_id"
        assert data["amount"] == 1000
        
        # Verify mock calls
        mock_create_allowance.assert_called_once()
    
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_invalid_admin_key(self, mock_require_admin_key, client, valid_allowance_data):
        """Test creating allowance with invalid admin key"""
        # Setup mocks to raise authentication error
        mock_require_admin_key.side_effect = HTTPException(status_code=403, detail="Admin key required")
        
        # Make request
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        
        # Assertions
        assert response.status_code == 403
    
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_missing_required_fields(self, mock_require_admin_key, client, mock_wallet):
        """Test creating allowance with missing required fields"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Test missing name
        invalid_data = {
            "lightning_address": "test@example.com",
            "amount": 1000,
            "currency": "sats",
            "start_date": "2024-01-01T00:00:00",
            "frequency_type": "daily",
            "next_payment_date": "2024-01-02T00:00:00",
            "memo": "Test memo",
            "active": True
        }
        
        response = client.post("/api/v1/allowance", json=invalid_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_invalid_amount(self, mock_require_admin_key, client, mock_wallet, valid_allowance_data):
        """Test creating allowance with invalid amount"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Test negative amount
        valid_allowance_data["amount"] = -100
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        assert response.status_code == 422
        
        # Test zero amount
        valid_allowance_data["amount"] = 0
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_invalid_lightning_address(self, mock_require_admin_key, client, mock_wallet, valid_allowance_data):
        """Test creating allowance with invalid lightning address"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Test empty lightning address
        valid_allowance_data["lightning_address"] = ""
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        assert response.status_code == 422
        
        # Test missing lightning address
        del valid_allowance_data["lightning_address"]
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_invalid_dates(self, mock_require_admin_key, client, mock_wallet, valid_allowance_data):
        """Test creating allowance with invalid date formats"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        
        # Test invalid date format
        valid_allowance_data["start_date"] = "invalid-date"
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        assert response.status_code == 422
    
    @patch('..views_api_minimal.create_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_database_error(self, mock_require_admin_key, mock_create_allowance, client, mock_wallet, valid_allowance_data):
        """Test creating allowance when database error occurs"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_create_allowance.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        
        # Assertions
        assert response.status_code == 500
    
    @patch('..views_api_minimal.create_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_with_custom_wallet(self, mock_require_admin_key, mock_create_allowance, client, mock_wallet, valid_allowance_data, mock_created_allowance):
        """Test creating allowance with custom wallet ID"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_created_allowance.wallet = "custom_wallet_id"
        mock_create_allowance.return_value = mock_created_allowance
        
        # Add custom wallet to data
        valid_allowance_data["wallet"] = "custom_wallet_id"
        
        # Make request
        response = client.post("/api/v1/allowance", json=valid_allowance_data)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["wallet"] == "custom_wallet_id"
    
    @patch('..views_api_minimal.create_allowance')
    @patch('..views_api_minimal.require_admin_key')
    def test_create_allowance_minimal_data(self, mock_require_admin_key, mock_create_allowance, client, mock_wallet, mock_created_allowance):
        """Test creating allowance with minimal required data"""
        # Setup mocks
        mock_require_admin_key.return_value = mock_wallet
        mock_create_allowance.return_value = mock_created_allowance
        
        # Minimal required data
        minimal_data = {
            "name": "Minimal Allowance",
            "lightning_address": "minimal@example.com",
            "amount": 500,
            "currency": "sats",
            "start_date": "2024-01-01T00:00:00",
            "frequency_type": "weekly",
            "next_payment_date": "2024-01-08T00:00:00",
            "memo": "Minimal memo"
        }
        
        # Make request
        response = client.post("/api/v1/allowance", json=minimal_data)
        
        # Assertions
        assert response.status_code == 201