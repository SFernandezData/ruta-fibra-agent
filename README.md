# ruta-fibra-agent

A quality report for a demo customer-support agent built on [ElevenAgents](https://elevenlabs.io). The agent plays the support line of a fictional fiber-internet provider, Ruta Fibra, and speaks Argentine Spanish.

## What this repository contains

- `reporte_agente.py`: a Python script that reads the agent's finished conversations through the ElevenLabs API. It writes one row per conversation to `conversaciones.csv` and a summary of pass rates to `reporte.md`. With `--tests`, it also runs the agent's test suite and reports the results.
- `.gitignore`: keeps the local `.env` file out of Git. That file holds the API key.

The API key and agent ID are not stored in this repository.

## What the script does

1. Lists every finished conversation for the agent, page by page.
2. Reads the evaluation criteria and data-collection results attached to each conversation.
3. Counts success, failure and unknown results for each criterion, and calculates a pass rate from the success and failure results only.
4. Optionally runs every test whose name starts with `RF - `, waits for the runs to finish, and prints a table of passed and failed results per test.

## Setup

1. Download or clone this repository.
2. Create a virtual environment and install the dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install requests python-dotenv
   ```

3. Create a file named `.env` in the same folder as the script:

   ```
   ELEVENLABS_API_KEY=your_key_here
   AGENT_ID=your_agent_id
   ```

## Usage

```bash
python reporte_agente.py                      # conversations only
python reporte_agente.py --tests --repeat 3   # also run the test suite 3 times
```

## Notes

- The API key needs access to the ElevenAgents endpoints.
- Test runs may use ElevenLabs credits.
- Requires Python 3.10 or newer.

## Author

Silvia Fernandez
