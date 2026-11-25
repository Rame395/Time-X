const path = require("path");

module.exports = {
  apps: [
    {
      name: "timex-backend",
      cwd: __dirname,
      script: path.join(__dirname, "run_server.py"),
      interpreter: path.join(__dirname, "venv", "bin", "python"),
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
  ],
};
