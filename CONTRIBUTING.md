# Contributing to ChatLens

Thank you for your interest in contributing to ChatLens! We welcome all contributions, including bug fixes, feature suggestions, documentation enhancements, and feedback.

Please follow these guidelines to make the contribution process smooth and productive for everyone.

---

## 🛠️ Local Development Setup

To contribute to ChatLens, you will need to set up the codebase locally. ChatLens v2.0 is composed of a Python/FastAPI backend and a React/Next.js frontend.

### ⚙️ Prerequisites
*   **Git**: For version control.
*   **Python (3.10+)**: For the FastAPI backend.
*   **Node.js (v18+)** and **npm**: For the Next.js frontend.
*   **Docker**: Highly recommended for running PostgreSQL (with `pgvector`) and Redis.

### 1. Fork & Clone
1.  Fork the repository on GitHub.
2.  Clone your fork locally:
    ```bash
    git clone https://github.com/YOUR_USERNAME/chatlens.git
    cd chatlens
    ```
3.  Set up the upstream remote:
    ```bash
    git remote add upstream https://github.com/tejaswin-amara/chatlens.git
    ```

### 2. Configure Environment
Create a `.env` file in the root directory (copying from `.env.example`):
```bash
cp .env.example .env
```
Ensure you add a valid `GEMINI_API_KEY` for AI testing.

### 3. Spin Up Services
Use Docker Compose to run the local PostgreSQL database (with vector support) and Redis:
```bash
docker-compose up -d
```

### 4. Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd chatlens-v2/backend
    ```
2.  Set up a virtual environment and activate it:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the development backend:
    ```bash
    uvicorn main:app --reload --port 8000
    ```
5.  In a separate terminal, start the Celery worker:
    ```bash
    celery -A celery_worker.celery_app worker --loglevel=info
    ```

### 5. Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd ../frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development web server:
    ```bash
    npm run dev
    ```
4.  Open `http://localhost:3000` in your browser.

---

## 🧪 Testing

We value test coverage. Before submitting a Pull Request, please run the test suite to ensure no functionality is broken:

```bash
# Run backend parser unit tests (ensure UTF-8 terminal encoding is set)
python -m tests.test_parsers
```

---

## 💅 Style & Linting Guidelines

### Backend (Python)
*   Format Python code using standard PEP 8 spacing rules.

### Frontend (TypeScript / React)
*   Ensure the linter passes without any errors or warnings before committing:
    ```bash
    cd chatlens-v2/frontend
    npm run lint
    ```

---

## 📥 Submitting a Pull Request (PR)

1.  **Create a branch** for your changes:
    ```bash
    git checkout -b feature/your-feature-name
    ```
2.  **Commit your changes** with a clear, descriptive message.
3.  **Push to your fork** on GitHub:
    ```bash
    git push origin feature/your-feature-name
    ```
4.  Open a Pull Request on the main repository, referencing any related open issues.

---

## ❓ Need Help?

If you have any questions or get stuck while contributing, feel free to open a Q&A issue or post in the discussion board!
