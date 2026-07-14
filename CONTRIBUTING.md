# 🤝 Contributing to ChatLens

Thank you for taking the time to contribute! ChatLens is a privacy-first, community-driven application, and we value your help in making it better.

Please review this guide to set up your local development environment and start contributing.

---

## 🛠️ Local Development Setup

ChatLens v2.0 is built on a split-service architecture: a **Next.js frontend** and a **FastAPI backend** running alongside **PostgreSQL** and **Redis**.

### ⚙️ Prerequisites

Before you begin, ensure you have the following installed:
*   **Git**: For version control.
*   **Python (3.10+)**: For the FastAPI backend and Celery workers.
*   **Node.js (v18+)** and **npm**: For the React web UI.
*   **Docker & Docker Compose**: To easily run PostgreSQL (`pgvector`) and Redis.

---

### 📥 1. Fork & Clone

1. Fork the [ChatLens Repository](https://github.com/tejaswin-amara/chatlens) on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/chatlens.git
   cd chatlens
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/tejaswin-amara/chatlens.git
   ```

---

### 🔧 2. Configuration

Create your local `.env` configuration file by copying the template:
```bash
cp .env.example .env
```
Open `.env` and configure your settings. You will need a **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/) to test AI functionalities.

---

### 📦 3. Run External Services

Spin up the local PostgreSQL database (with `pgvector` pre-installed) and Redis broker using Docker:
```bash
docker-compose up -d
```

---

### 🐍 4. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd chatlens-v2/backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
5. In a separate terminal, activate the venv and start the Celery worker task runner:
   ```bash
   celery -A celery_worker.celery_app worker --loglevel=info
   ```

---

### ⚛️ 5. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd chatlens-v2/frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server with Turbopack:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Validation

Please ensure all tests and linters pass cleanly before proposing a Pull Request:

### 🐍 Python Backend Tests
Run the parser self-checks from the root directory:
```bash
# Set console encoding to UTF-8 on Windows before running:
# $env:PYTHONIOENCODING="utf-8"
python -m tests.test_parsers
```

### ⚛️ Frontend Linting
Run ESLint to check for code issues:
```bash
cd chatlens-v2/frontend
npm run lint
```

---

## 🚀 Submitting a Pull Request (PR)

1. Create a branch for your changes:
   ```bash
   git checkout -b feature/amazing-feature
   ```
2. Write clean, readable code and document your changes.
3. Commit with clear messages:
   ```bash
   git commit -m "feat: add support for WhatsApp media timestamps"
   ```
4. Push to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request on the main repository, referencing any related open issues.

---

> [!TIP]
> **Need help?** Open a Q&A issue on GitHub or join our community discussions. We are happy to guide new contributors!
