const path = require("path");

module.exports = {
  apps: [
    {
      name: "timex-backend",
      cwd: __dirname,
      script: path.join(__dirname, "venv", "bin", "uvicorn"),
      args: "app.main:app --host 127.0.0.1 --port 8000 --workers 2",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
  ],
};
