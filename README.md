# do-control

A distributed load testing system designed to provision, manage, and orchestrate synchronized testing across multiple DigitalOcean droplets.

## Project Status

**Early Development** - Core components implemented:
- Management Console API with droplet provisioning
- Agent communication architecture
- Command execution framework
- Time synchronization for distributed testing
- Database models and basic authentication

Coming soon:
- Web interface
- Advanced metrics visualization
- Test result analysis features
- Enhanced agent deployment options

## Features

- Automated provisioning of test infrastructure across multiple geographic regions
- Precise coordination of test execution across all provisioned resources
- Comprehensive monitoring and analysis of test results and resource utilization
- Simplified management of complex distributed testing scenarios

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- DigitalOcean API Token

### Environment Setup

1. Clone the repository
   ```
   git clone https://github.com/omerbustun/do-control.git
   cd do-control
   ```

2. Create a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```
   export DO_API_TOKEN=your_digitalocean_token
   ```

### Running with Docker Compose

This will start the full system with a management console, database, RabbitMQ, and simulated agents:

```
docker-compose up
```

Access the API at http://localhost:8000 and the Swagger UI at http://localhost:8000/docs

### Running Components Individually

1. Start PostgreSQL and RabbitMQ
   ```
   docker-compose up -d db rabbitmq
   ```

2. Run database migrations
   ```
   alembic upgrade head
   ```

3. Start the management console
   ```
   uvicorn console.main:app --reload
   ```

4. Start an agent
   ```
   python agent/main.py
   ```

## Testing

Run unit tests:
```
pytest
```

## License

GPL-3.0