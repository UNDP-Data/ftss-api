"""
Tests for email services.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.services.msgraph_service import MSGraphEmailService
from src.services.sendgrid_service import SendGridEmailService

client = TestClient(app)

@pytest.fixture
def mock_msgraph_client():
    with patch('src.services.msgraph_service.GraphClient') as mock:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_sendgrid_client():
    with patch('src.services.sendgrid_service.SendGridAPIClient') as mock:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_instance.send = MagicMock(return_value=mock_response)
        mock.return_value = mock_instance
        yield mock_instance

@pytest.mark.asyncio
async def test_msgraph_send_email(mock_msgraph_client):
    """Test sending email via Microsoft Graph API"""
    # Setup
    service = MSGraphEmailService()
    
    # Test
    result = await service.send_email(
        to_emails=["test@example.com"],
        subject="Test Subject",
        content="Test Content"
    )
    
    # Assert
    assert result is True
    mock_msgraph_client.post.assert_called_once()
    call_args = mock_msgraph_client.post.call_args[0]
    assert call_args[0] == "/me/sendMail"

@pytest.mark.asyncio
async def test_msgraph_send_notification(mock_msgraph_client):
    """Test sending notification via Microsoft Graph API"""
    # Setup
    service = MSGraphEmailService()
    
    # Test
    result = await service.send_notification_email(
        to_email="test@example.com",
        subject="Test Notification",
        template_id="test-template",
        dynamic_data={"name": "Test User"}
    )
    
    # Assert
    assert result is True
    mock_msgraph_client.post.assert_called_once()
    call_args = mock_msgraph_client.post.call_args[0]
    assert call_args[0] == "/me/sendMail"

@pytest.mark.asyncio
async def test_sendgrid_send_email(mock_sendgrid_client):
    """Test sending email via SendGrid"""
    # Setup
    service = SendGridEmailService()
    
    # Test
    result = await service.send_email(
        to_emails=["test@example.com"],
        subject="Test Subject",
        content="Test Content"
    )
    
    # Assert
    assert result is True
    mock_sendgrid_client.send.assert_called_once()

@pytest.mark.asyncio
async def test_sendgrid_send_notification(mock_sendgrid_client):
    """Test sending notification via SendGrid"""
    # Setup
    service = SendGridEmailService()
    
    # Test
    result = await service.send_notification_email(
        to_email="test@example.com",
        subject="Test Notification",
        template_id="test-template",
        dynamic_data={"name": "Test User"}
    )
    
    # Assert
    assert result is True
    mock_sendgrid_client.send.assert_called_once()

@pytest.mark.skip(reason="Requires database connection")
def test_email_endpoints(headers: dict):
    """Test email endpoints with authentication"""
    # Test send email endpoint
    response = client.post(
        "/email/send",
        json={
            "to_emails": ["test@example.com"],
            "subject": "Test Subject",
            "content": "Test Content"
        },
        headers=headers
    )
    assert response.status_code in [200, 403]  # 200 if admin, 403 if not admin

    # Test notification endpoint
    response = client.post(
        "/email/notify",
        json={
            "to_email": "test@example.com",
            "subject": "Test Notification",
            "template_id": "test-template",
            "dynamic_data": {"name": "Test User"}
        },
        headers=headers
    )
    assert response.status_code in [200, 403]  # 200 if admin, 403 if not admin
