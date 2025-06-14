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
def mock_allowances():
    return [
        Allowance(
            id="allowance_1",
            name="Test Allowance 1",
            wallet="test_wallet_id",
            lightning_address="test1@example.com",
            amount=1000,
            currency="sats",
            start_date=datetime(2024, 1, 1),
            frequency_type="daily",
            next_payment_date=datetime(2024, 1, 2),
            memo="Test memo 1",
            active=True
        ),
        Allowance(
            id="allowance_2",
            name="Test Allowance 2",
            wallet="test_wallet_id",
            lightning_address="test2@example.com",
            amount=2000,
            currency="sats",
            start_date=datetime(2024, 1, 1),
            frequency_type="weekly",
            next_payment_date=datetime(2024, 1, 8),
            memo="Test memo 2",
            active=False
        )
    ]


class TestListAllowancesAPI:
    
    @patch('..views_api_minimal.get_allowances')
    @patch('..views_api_minimal.require_invoice_key')
    def test_list_allowances_success(self, mock_require_invoice_key, mock_get_allowances, client, mock_wallet, mock_allowances):
        """Test successful listing of allowances"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowances.return_value = mock_allowances
        
        # Make request
        response = client.get("/api/v1/allowance")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "allowance_1"
        assert data[0]["name"] == "Test Allowance 1"
        assert data[1]["id"] == "allowance_2"
        assert data[1]["name"] == "Test Allowance 2"
        
        # Verify mock calls
        mock_get_allowances.assert_called_once_with([mock_wallet.wallet.id])
    
    @patch('..views_api_minimal.get_allowances')
    @patch('..views_api_minimal.require_invoice_key')
    def test_list_allowances_empty(self, mock_require_invoice_key, mock_get_allowances, client, mock_wallet):
        """Test listing allowances when none exist"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowances.return_value = []
        
        # Make request
        response = client.get("/api/v1/allowance")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        assert data == []
    
    @patch('..views_api_minimal.require_invoice_key')
    def test_list_allowances_invalid_key(self, mock_require_invoice_key, client):
        """Test listing allowances with invalid API key"""
        # Setup mocks to raise authentication error
        mock_require_invoice_key.side_effect = HTTPException(status_code=401, detail="Invalid key")
        
        # Make request
        response = client.get("/api/v1/allowance")
        
        # Assertions
        assert response.status_code == 401
    
    @patch('..views_api_minimal.get_allowances')
    @patch('..views_api_minimal.require_invoice_key')
    def test_list_allowances_database_error(self, mock_require_invoice_key, mock_get_allowances, client, mock_wallet):
        """Test listing allowances when database error occurs"""
        # Setup mocks
        mock_require_invoice_key.return_value = mock_wallet
        mock_get_allowances.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.get("/api/v1/allowance")
        
        # Assertions
        assert response.status_code == 500