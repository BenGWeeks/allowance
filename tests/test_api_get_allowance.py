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


class TestGetAllowanceAPI:
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_success(self, mock_require_invoice_key, mock_get_allowance, client, mock_wallet, mock_allowance):
        """Test successful retrieval of a single allowance"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowance.return_value = mock_allowance
        
        # Make request
        response = client.get("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_allowance_id"
        assert data["name"] == "Test Allowance"
        assert data["wallet"] == "test_wallet_id"
        assert data["lightning_address"] == "test@example.com"
        assert data["amount"] == 1000
        assert data["currency"] == "sats"
        assert data["frequency_type"] == "daily"
        assert data["memo"] == "Test memo"
        assert data["active"] is True
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test_allowance_id")
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_not_found(self, mock_require_invoice_key, mock_get_allowance, client, mock_wallet):
        """Test getting allowance that doesn't exist"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowance.return_value = None
        
        # Make request
        response = client.get("/api/v1/allowance/nonexistent_id")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Allowance does not exist."
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("nonexistent_id")
    
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_invalid_key(self, mock_require_invoice_key, client):
        """Test getting allowance with invalid API key"""
        # Setup mocks to raise authentication error
        mock_require_invoice_key.side_effect = HTTPException(status_code=401, detail="Invalid key")
        
        # Make request
        response = client.get("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 401
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_database_error(self, mock_require_invoice_key, mock_get_allowance, client, mock_wallet):
        """Test getting allowance when database error occurs"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowance.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.get("/api/v1/allowance/test_allowance_id")
        
        # Assertions
        assert response.status_code == 500
    
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_empty_id(self, mock_require_invoice_key, client, mock_wallet):
        """Test getting allowance with empty ID"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        
        # Make request with empty ID
        response = client.get("/api/v1/allowance/")
        
        # Assertions - should return 404 for malformed URL
        assert response.status_code == 404
    
    @patch('..views_api_minimal.get_allowance')
    @patch('..views_api_minimal.require_invoice_key')
    def test_get_allowance_special_characters(self, mock_require_invoice_key, mock_get_allowance, client, mock_wallet, mock_allowance):
        """Test getting allowance with special characters in ID"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_allowance.id = "test-allowance_123"
        mock_get_allowance.return_value = mock_allowance
        
        # Make request
        response = client.get("/api/v1/allowance/test-allowance_123")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-allowance_123"
        
        # Verify mock calls
        mock_get_allowance.assert_called_once_with("test-allowance_123")