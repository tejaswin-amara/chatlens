# SPARK PA Daemon Deployment

1. Create a `spark` user:
   ```bash
   sudo useradd -m -s /bin/bash spark
   ```

2. Clone repository to `/opt/chatlens` and configure `.env` (ensure `chmod 600` for `.env` and token files).
3. Setup `uv` for the `spark` user.

4. Install the service:
   ```bash
   sudo cp deploy/spark.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable spark
   sudo systemctl start spark
   ```

5. View logs:
   ```bash
   journalctl -u spark -f
   ```

### Notes
- Only one instance may run at a time (a second instance causes bot 409 conflicts).
- Nightly backup script: `sqlite3 /opt/chatlens/spark.db ".backup /tmp/spark.bak"`
