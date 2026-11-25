const path = require("path");

module.exports = {
  apps: [
    {
      name: "timex-backend",
      cwd: __dirname,
      script: path.join(__dirname, "start.sh"),
      interpreter: "/bin/bash",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
  ],
};
