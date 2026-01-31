# friction Setup Instructions

## Prerequisites
- **Python 3.9+**
- **Node.js 18+**
- **Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

## One-Time Setup

1.  **Backend (Python Service)**
    ```bash
    cd service
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configuration**
    - Copy the example environment file:
      ```bash
      cp service/.env.example service/.env
      ```
    - Edit `service/.env` and paste your `GEMINI_API_KEY`.

3.  **Frontend (Electron App)**
    ```bash
    cd app
    npm install
    ```

## Running the App (Dev Mode)

To run both the Python Service and the Electron App together:

```bash
./start_app.sh
```

Ensure the script is executable: `chmod +x start_app.sh`.

## Manual Run (Separate Terminals)

**Terminal 1 (Service):**
```bash
./start_service.sh
```

**Terminal 2 (App):**
```bash
cd app
npm run electron:dev
```

## Packaging for Distribution

To build a standalone application (Mac .app):

```bash
cd app
npm run build         # Builds React code
# For simple packaging (requires electron-packager or builder config)
# Add "electron-builder" script usage in package.json if desired.
# Currently set up for Local Dev.
```
