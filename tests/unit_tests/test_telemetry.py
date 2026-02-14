
def test_create_telemetry(client):
    """Test POST /telemetry - Create new telemetry entry"""
    payload = {
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    }
    
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["satelliteId"] == "sattelite-1"
    assert data["altitude"] == 550.0
    assert data["velocity"] == 7.6
    assert data["status"] == "healthy"
    assert "id" in data
    assert "created" in data
    assert "updated" in data


def test_create_telemetry_invalid_status(client):
    """Test POST /telemetry - Reject invalid status"""
    payload = {
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "unknown"  # Invalid status
    }
    
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422  # Validation error


def test_create_telemetry_satellite_id_too_long(client):
    """Test POST /telemetry - Reject satelliteId longer than 64 chars"""
    payload = {
        "satelliteId": "S" * 65,
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    }

    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422


def test_create_telemetry_satellite_id_max_length(client):
    """Test POST /telemetry - Accept satelliteId with exactly 64 chars"""
    sid = "S" * 64
    payload = {
        "satelliteId": sid,
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    }

    response = client.post("/telemetry", json=payload)
    assert response.status_code == 200
    assert response.json()["satelliteId"] == sid


def test_create_telemetry_invalid_timestamp(client):
    """Test POST /telemetry - Reject invalid timestamp"""
    payload = {
        "satelliteId": "sattelite-1",
        "timestamp": "not-a-timestamp",  # Invalid timestamp format
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    }

    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422


def test_create_telemetry_invalid_altitude(client):
    """Test POST /telemetry - Reject negative altitude"""
    payload = {
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": -100,  # Invalid
        "velocity": 7.6,
        "status": "healthy"
    }
    
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422

    # Test edge case of zero altitude
    payload ["altitude"] = 0 # invalid    
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422


def test_create_telemetry_invalid_velocity(client):
    """Test POST /telemetry - Reject invalid velocity"""
    payload = {
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": -7.2, # invalid 
        "status": "healthy"
    }

    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422

    # Test edge case of zero velocity
    """Test POST /telemetry - Reject invalid velocity"""
    payload ["velocity"] = 0 # invalid
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422





def test_list_telemetry(client):
    """Test GET /telemetry - List all telemetry"""
    # Create test data
    client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-002",
        "timestamp": "2026-02-14T11:00:00",
        "altitude": 20200.0,
        "velocity": 3.9,
        "status": "critical"
    })
    
    response = client.get("/telemetry")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["satelliteId"] == "SAT-002"
    assert data["items"][1]["satelliteId"] == "sattelite-1"


def test_list_telemetry_filter_by_satellite(client):
    """Test GET /telemetry - Filter by satelliteId"""
    # Create test data
    client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T12:00:00",
        "altitude": 600.0,
        "velocity": 7.7,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-002",
        "timestamp": "2026-02-14T11:00:00",
        "altitude": 20200.0,
        "velocity": 3.9,
        "status": "critical"
    })
    
    response = client.get("/telemetry?satelliteId=sattelite-1")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["timestamp"] == "2026-02-14T12:00:00"
    assert data["items"][1]["timestamp"] == "2026-02-14T10:00:00"
    assert data["items"][0]["satelliteId"] == "sattelite-1"


def test_list_telemetry_filter_by_status(client):
    """Test GET /telemetry - Filter by status"""
    # Create test data
    client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-002",
        "timestamp": "2026-02-14T11:00:00",
        "altitude": 20200.0,
        "velocity": 3.9,
        "status": "critical"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-003",
        "timestamp": "2026-02-14T12:00:00",
        "altitude": 35786.0,
        "velocity": 3.1,
        "status": "critical"
    })
    
    response = client.get("/telemetry?status=critical")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["timestamp"] == "2026-02-14T12:00:00"
    assert data["items"][1]["timestamp"] == "2026-02-14T11:00:00"
    assert data["items"][0]["status"] == "critical"


def test_list_telemetry_filter_by_satellite_and_status(client):
    """Test GET /telemetry - Filter by satelliteId AND status"""
    # Create test data
    client.post("/telemetry", json={
        "satelliteId": "SAT-001",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-001",
        "timestamp": "2026-02-14T12:00:00",
        "altitude": 600.0,
        "velocity": 7.7,
        "status": "critical"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-002",
        "timestamp": "2026-02-14T11:00:00",
        "altitude": 20200.0,
        "velocity": 3.9,
        "status": "critical"
    })

    response = client.get("/telemetry?satelliteId=SAT-001&status=critical")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["satelliteId"] == "SAT-001"
    assert data["items"][0]["status"] == "critical"
    assert data["items"][0]["timestamp"] == "2026-02-14T12:00:00"


def test_list_telemetry_timestamp_desc_order(client):
    """Test GET /telemetry - Always return data in timestamp descending order"""
    # Create test data
    client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    client.post("/telemetry", json={
        "satelliteId": "SAT-002",
        "timestamp": "2026-02-14T11:00:00",
        "altitude": 20200.0,
        "velocity": 3.9,
        "status": "critical"
    })
    
    response = client.get("/telemetry")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["timestamp"] == "2026-02-14T11:00:00"
    assert data["items"][1]["timestamp"] == "2026-02-14T10:00:00"


def test_pagination_page_size(client):
    """Test GET /telemetry - Pagination with custom page size"""
    # Create 5 records
    for i in range(5):
        client.post("/telemetry", json={
            "satelliteId": f"SAT-{i:03d}",
            "timestamp": f"2026-02-14T{10+i:02d}:00:00",
            "altitude": 500.0 + i * 100,
            "velocity": 7.0 + i * 0.1,
            "status": "healthy"
        })
    
    # Request with size=2 (2 items per page)
    response = client.get("/telemetry?size=2")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["size"] == 2


def test_pagination_multiple_pages(client):
    """Test GET /telemetry - Navigate through multiple pages"""
    # Create 5 records
    for i in range(5):
        client.post("/telemetry", json={
            "satelliteId": f"SAT-{i:03d}",
            "timestamp": f"2026-02-14T{10+i:02d}:00:00",
            "altitude": 500.0 + i * 100,
            "velocity": 7.0 + i * 0.1,
            "status": "healthy"
        })
    
    # Get first page (2 items)
    response1 = client.get("/telemetry?size=2&page=1")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["items"]) == 2
    first_page_ids = [item["id"] for item in data1["items"]]
    
    # Get second page (2 items)
    response2 = client.get("/telemetry?size=2&page=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2
    second_page_ids = [item["id"] for item in data2["items"]]
    
    # Page IDs should not overlap
    assert not set(first_page_ids) & set(second_page_ids)


def test_pagination_with_filter(client):
    """Test GET /telemetry - Pagination with filters"""
    # Create 3 healthy and 3 critical records
    for i in range(3):
        client.post("/telemetry", json={
            "satelliteId": f"SAT-{i:03d}",
            "timestamp": f"2026-02-14T{10+i:02d}:00:00",
            "altitude": 500.0 + i * 100,
            "velocity": 7.0 + i * 0.1,
            "status": "healthy"
        })
    for i in range(3):
        client.post("/telemetry", json={
            "satelliteId": f"SAT-CRIT-{i:03d}",
            "timestamp": f"2026-02-14T{13+i:02d}:00:00",
            "altitude": 20000.0 + i * 100,
            "velocity": 3.5 + i * 0.1,
            "status": "critical"
        })
    
    # Request critical records with pagination
    response = client.get("/telemetry?status=critical&size=2")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert all(item["status"] == "critical" for item in data["items"])


def test_get_telemetry_by_id(client):
    """Test GET /telemetry/{id} - Get specific telemetry entry"""
    # Create test data
    create_response = client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    telemetry_id = create_response.json()["id"]
    
    response = client.get(f"/telemetry/{telemetry_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == telemetry_id
    assert data["satelliteId"] == "sattelite-1"


def test_get_telemetry_not_found(client):
    """Test GET /telemetry/{id} - 404 for non-existent entry"""
    response = client.get("/telemetry/99999")
    assert response.status_code == 404


def test_delete_telemetry(client):
    """Test DELETE /telemetry/{id} - Delete telemetry entry"""
    # Create test data
    create_response = client.post("/telemetry", json={
        "satelliteId": "sattelite-1",
        "timestamp": "2026-02-14T10:00:00",
        "altitude": 550.0,
        "velocity": 7.6,
        "status": "healthy"
    })
    telemetry_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(f"/telemetry/{telemetry_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == telemetry_id
    assert data["message"] == "Telemetry record deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/telemetry/{telemetry_id}")
    assert get_response.status_code == 404


def test_delete_telemetry_not_found(client):
    """Test DELETE /telemetry/{id} - 404 for non-existent entry"""
    response = client.delete("/telemetry/99999")
    assert response.status_code == 404
