# Deployment Guide

## Quick Deploy

```bash
# 1. Install
cd deployment
./install.sh

# 2. Configure
cp ../config/env.example ../.env
nano ../.env  # Add your credentials

# 3. Initialize database
cd ../src/scripts
./recreate_database.sh

# 4. Start services
cd ../main
python3 sage4_interface_fixed.py &
python3 scrapex_admin.py &
```

## Access
- Main: http://localhost:8540
- Admin: http://localhost:8543

## Services

### Main Interface
```bash
python3 /home/ubuntu/newspaper_project/src/main/sage4_interface_fixed.py &
```

### Admin Interface
```bash
python3 /home/ubuntu/newspaper_project/src/main/scrapex_admin.py &
```

## Logs
```bash
tail -f /home/ubuntu/logs/sage.log
tail -f /home/ubuntu/logs/admin.log
```
