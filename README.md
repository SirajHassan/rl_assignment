# Telemetry API

FastAPI service for storing and querying satellite telemetry records.

---

## Summary 
 This API was built using Python3.11, the FastAPI framework, SQLite as a database and runs in a Docker container. 
 
 My approach was to use the features of FastAPI and pydantic validation to create endpoints in line with what was requested in the assignment. In the SQLite database I created a Telemetry table with columns and constraints for the expected telemetry data. 

 Directory structure was built around what is suggested in the FAST API tutorial: https://fastapi.tiangolo.com/tutorial/bigger-applications/

 Important Files:
 - [Telemertry API](https://github.com/SirajHassan/rl_assignment/blob/main/app/routers/telemetry.py)
 - [Database Model](https://github.com/SirajHassan/rl_assignment/blob/main/app/db/models.py)
 - [Unit test](https://github.com/SirajHassan/rl_assignment/blob/main/tests/unit_tests/test_telemetry.py)
 - [System test](https://github.com/SirajHassan/rl_assignment/blob/main/tests/system_tests/load_test_telemetry.py)

## Assumptions
  - `satelliteId` values are strings with a max of 64 characters
  - `velocity` and `altitude` use floating-point values for precision
  - `velocity` is assumed to be km/s in the API docs
  - `altitude` is assumed to be km in the API docs
  - `status` has been enumerated to only have the valid values `healthy` or `critical`
  - `created` and `updated` are server-managed timestamp columns, which I thought would be helpful for comparing telemetry timestamps to the time they were recieved

## Requirements

- Docker + Docker Compose for running the server and unit tests
- If you want to run the system tests, python 3.11 is downloaded on your machine
---

## Run with Docker

From the project root run the container in the foreground so the server is up and logs are printed to your terminal:

```bash
# build image
docker compose build

# run in foreground
docker compose up
```

## Swagger Docs
API Docs will be available at `http://localhost:8000` when the server is running.

---

## API endpoints

- POST `/telemetry` — create telemetry record
  - Request body example available in docs (see POST examples in Swagger)
  - Example curl (create a telemetry record):

    ```bash
    curl -s -X POST "http://localhost:8000/telemetry" \
      -H "Content-Type: application/json" \
      -d '{"satelliteId":"sattelite-1","timestamp":"2026-02-14T10:00:00","altitude":550.0,"velocity":7.6,"status":"healthy"}'
    ```

- GET `/telemetry` — list telemetry (paginated, newest first)
  - Query params: `page` (default 1), `size` (default 50), `satelliteId`, `status`
  - Example curl (get first page, default size):

    ```bash
    curl -s "http://localhost:8000/telemetry"
    ```

  Responses for pages follow the `fastapi-pagination` format:

    ```json
    {
      "items": [ /* telemetry objects */ ],
      "total": 123,
      "page": 1,
      "size": 50,
      "pages": 3
    }
    ```

  - Example curl (filter by status + page/size):

    ```bash
    curl -s "http://localhost:8000/telemetry?status=critical&page=1&size=10"
    ```

  - Example curl (filter by satelliteId):

    ```bash
    curl -s "http://localhost:8000/telemetry?satelliteId=sattelite-1"
    ```

- GET `/telemetry/{id}` — retrieve a telemetry entry
  - Example curl:

    ```bash
    curl -s "http://localhost:8000/telemetry/1"
    ```

- DELETE `/telemetry/{id}` — delete an entry
  - Example curl:

    ```bash
    curl -s -X DELETE "http://localhost:8000/telemetry/1"
    ```


---

## Tests

### Unit Tests

Unit tests were made to test each endpoint and also edge cases within the docker container. 

- Run in Docker:

  ```bash
  docker compose run --rm api pytest
  ```

### System Test

This script creates a larger amount of telemetry and validates API behaviour at a higher scale. Optionally it writes `first_page_results.csv` (use the `--create-file` flag).

Requirements
- Python 3.11

Run the script locally
1. Start the API:

   ```bash
   docker compose up
   ```

2. In another terminal (or run Docker in the background), run the system test from the project root:

   ```bash
   python3 tests/system_tests/load_test_telemetry.py --url http://localhost:8000/telemetry --total 1000 --concurrency 100 --create-file
   ```
