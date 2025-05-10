# HTTP Tarpit & Bot Analyzer 🛡️

A Python-based HTTP tarpit designed to slow down malicious bots, collect data about their activities, report them to AbuseIPDB, and provide data for analysis and visualization.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

## ✨ Features

*   **Asynchronous HTTP Tarpit**: Built with `aiohttp` to efficiently handle numerous slow connections.
*   **Dynamic Slowdown**: Configurable delay and response size to "freeze" clients.
*   **Detailed Data Collection**: Logs IP, port, HTTP method, path, full headers, User-Agent, session duration, etc.
*   **GeoIP Enrichment**: Identifies country, city, coordinates, and ASN інформації for each IP using local MaxMind GeoLite2 databases.
*   **Structured Storage**: Events are stored in a local SQLite database for convenient querying and analysis.
*   **JSON Logging**: Parallel JSON file logging for debugging and potential integration with external logging systems.
*   **AbuseIPDB Integration**: Automatically reports suspicious IPs to [AbuseIPDB](https://www.abuseipdb.com/) via their API v2.
*   **Flexible Configuration**: Server parameters, logging, database paths, and API keys are managed via a configuration module and an `.env` file.

## 🛠️ Tech Stack

*   **Language**: Python (3.10+)
*   **Async**: `asyncio`, `aiohttp`
*   **Project Management**: `Poetry`
*   **Configuration**: `python-dotenv`
*   **Geolocation**: `geoip2-python`
*   **Database**: `sqlite3` 
*   **Analysis**: `pandas`
*   **Visualization**: `matplotlib`, `seaborn`, `folium`
*   **Deployment**: Nginx, Certbot (Let's Encrypt), Systemd, Docker

## 🚀 Getting Started (Local Setup)

### Prerequisites

*   Python 3.10 or newer
*   Poetry (Python dependency manager)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/t1a0/http-tarpit.git http-tarpit
    cd http-tarpit
    ```

2.  **Install Poetry** (if not already installed):
    Follow the instructions on the [official Poetry website](https://python-poetry.org/docs/#installation).

3.  **Install project dependencies:**
    ```bash
    poetry install --no-dev
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the project root and add your AbuseIPDB API key:
    ```env
    # .env
    ABUSEIPDB_API_KEY=YOUR_ABUSEIPDB_API_KEY
    ```

5.  **Set up GeoIP databases:**
    *   Download the free `GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb` databases from [MaxMind](https://www.maxmind.com/en/geolite2/signup).
    *   Create a `data/` directory in the project root (if it doesn't exist).
    *   Place the downloaded `.mmdb` files into the `data/` directory.

6.  **Initialize SQLite Database:**
    The database (`data/tarpit_events.db`) and its table will be created automatically on the first run if the DB file doesn't exist.

### Running the Application

To start the HTTP tarpit, execute the following command from the project root:

```bash
poetry run python main.py