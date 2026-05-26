module.exports = {
  apps: [
    {
      name: "sodigaz-locator-backend",
      script: "venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8002",
      cwd: "/home/debian/apps/sodigaz-geolocbackend",
      interpreter: "none", // Utilise directement l'exécutable uvicorn du venv
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        PYTHONPATH: ".",
        PORT: 8002
      }
    }
  ]
};
