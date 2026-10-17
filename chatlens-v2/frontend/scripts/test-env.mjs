process.env.KL_SYNC_DEMO_MODE = process.env.KL_SYNC_DEMO_MODE ?? 'true';
process.env.KL_SYNC_AI_MODE = process.env.KL_SYNC_AI_MODE ?? 'offline';
process.env.SESSION_SECRET =
  process.env.SESSION_SECRET ?? 'ci-test-secret-key-32-chars-long!!';
