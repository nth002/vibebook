# VibeBook - Deployment Guide (MySQL)

Complete guide for deploying VibeBook Django application to production with MySQL database.

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 10+
- **Python**: 3.8+
- **Database**: MySQL 8.0+
- **Web Server**: Nginx
- **Application Server**: Gunicorn
- **RAM**: Minimum 1GB
- **Storage**: Minimum 10GB

### Domain & SSL
- Domain name pointing to your server IP
- SSL certificate (Let's Encrypt recommended)

---

## 🚀 Deployment Option 1: Ubuntu Server with MySQL (Recommended)

### Step 1: System Update
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx mysql-server mysql-client git supervisor libmysqlclient-dev -y