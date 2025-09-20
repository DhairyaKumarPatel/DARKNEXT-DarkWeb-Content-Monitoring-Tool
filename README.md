# DARKNEXT - Dark Web Content Monitor (Lite Version)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Educational-yellow.svg)

## ⚠️ IMPORTANT DISCLAIMER

This tool is intended for **EDUCATIONAL AND RESEARCH PURPOSES ONLY**. The use of this tool for illegal activities is strictly prohibited. Users are responsible for compliance with all applicable laws and regulations. The authors assume no liability for misuse of this software.

## 📋 Overview

DARKNEXT is a Python-based OSINT (Open Source Intelligence) tool designed to passively monitor dark web content through the Tor network. It crawls `.onion` sites, searches for specific keywords, extracts entities, and provides automated alerts when relevant findings are discovered.

### 🎯 Core Features

1. **Tor-based Web Crawler** - Crawl `.onion` sites using Tor proxy with configurable settings
2. **Keyword Matching & Entity Extraction** - Search for predefined keywords and extract entities like emails, cryptocurrency addresses, and PGP keys
3. **Data Storage & Archiving** - Store findings in MongoDB with optional raw HTML archiving
4. **Alert System** - Send notifications via Telegram, email, or file alerts when matches are found

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Tor Browser or Tor service running
- MongoDB (optional, file storage available as fallback)

### Installation

1. **Clone or download the project**
2. **Navigate to the DARKNEXT directory**
3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Setup Tor** (see detailed instructions below)
6. **Configure the application** (see configuration section)

### Basic Usage

```bash
# Test all components
python src/main.py --mode test

# Run a single scan
python src/main.py --mode single

# Run continuous monitoring (default 1 hour interval)
python src/main.py --mode continuous

# View statistics
python src/main.py --mode stats

# Custom configuration and URLs
python src/main.py --config custom_config.yaml --urls custom_urls.txt
```

## 🔧 Installation & Setup

### 1. Tor Installation

#### Windows
1. Download Tor Browser from https://www.torproject.org/
2. Install and run Tor Browser
3. Alternatively, install Tor as a service:
   - Download Tor Expert Bundle
   - Extract and run `tor.exe`
   - Default SOCKS proxy will be on `127.0.0.1:9050`

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install tor
sudo systemctl start tor
sudo systemctl enable tor
```

#### macOS
```bash
brew install tor
brew services start tor
```

### 2. MongoDB Setup (Optional)

#### Using Docker
```bash
docker run -d --name mongodb -p 27017:27017 mongo:latest
```

#### Native Installation
- **Ubuntu/Debian**: `sudo apt install mongodb`
- **macOS**: `brew install mongodb/brew/mongodb-community`
- **Windows**: Download from https://www.mongodb.com/try/download/community

### 3. Environment Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your configuration:
   ```bash
   # Telegram Bot Configuration (for alerts)
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   
   # Email Configuration (for alerts)
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password_here
   EMAIL_RECIPIENT=alerts@example.com
   
   # MongoDB (if using remote instance)
   MONGODB_URI=mongodb://localhost:27017
   ```

### 4. Configuration Files

#### Keywords Configuration (`config/keywords.txt`)
Add keywords you want to monitor (one per line):
```
vulnerability
exploit
ransomware
bitcoin
database leak
# Add your keywords here
```

#### URLs Configuration (`config/onion_urls.txt`)
Add .onion URLs to monitor (one per line):
```
http://example1abcdefghijklmnopqrstuvwxyz.onion
http://example2abcdefghijklmnopqrstuvwxyz.onion
# Add legitimate .onion URLs for monitoring
```

**⚠️ Important**: Only add URLs from legitimate sources and ensure your monitoring activities comply with applicable laws.

## ⚙️ Configuration

The main configuration is in `config/config.yaml`. Key sections:

### Tor Settings
```yaml
tor:
  proxy_host: "127.0.0.1"
  proxy_port: 9050
  timeout: 30
  max_retries: 3
```

### Crawler Settings
```yaml
crawler:
  max_pages_per_site: 10
  delay_between_requests: 5
  max_concurrent_requests: 3
  page_timeout: 60
```

### Alert Settings
```yaml
alerts:
  enabled: true
  methods: ["telegram"]  # Options: telegram, email, file
  telegram:
    bot_token: "YOUR_BOT_TOKEN_HERE"
    chat_id: "YOUR_CHAT_ID_HERE"
```

## 🔍 Usage Examples

### Basic Monitoring
```bash
# Single scan with verbose output
python src/main.py --mode single --verbose

# Continuous monitoring every 2 hours
python src/main.py --mode continuous --interval 7200

# Test configuration and connections
python src/main.py --mode test
```

### Custom Operations
```bash
# Use custom configuration
python src/main.py --config my_config.yaml

# Use custom URL list
python src/main.py --urls my_onion_sites.txt

# Combine options
python src/main.py --mode continuous --config prod_config.yaml --interval 3600
```

## 📊 Output & Results

### Database Storage
- **MongoDB**: Findings stored in structured format
- **File Storage**: JSONL format as fallback
- **Raw HTML**: Optionally archived in `/archive` directory

### Alert Format
When matches are found, alerts include:
- URL and page title
- Timestamp of discovery
- Matched keywords with context
- Extracted entities (emails, crypto addresses, etc.)
- Content preview

### Statistics
View monitoring statistics:
```bash
python src/main.py --mode stats
```

## 🔒 Security Considerations

### Best Practices
1. **Use VPN + Tor** for additional anonymity
2. **Run in isolated environment** (VM recommended)
3. **Regular updates** of Tor and dependencies
4. **Monitor resource usage** to avoid detection
5. **Respect rate limits** and site policies

### Ethical Guidelines
- Only monitor publicly accessible content
- Respect robots.txt and site terms
- Do not attempt to login or authenticate
- Do not engage in any transactions
- Report illegal content to appropriate authorities

## 🛠️ Development

### Project Structure
```
DARKNEXT/
├── src/
│   ├── __init__.py
│   ├── main.py              # Main application
│   ├── tor_crawler.py       # Tor crawler implementation
│   ├── content_parser.py    # Content parsing and keyword matching
│   ├── database_handler.py  # Database operations
│   ├── alert_system.py      # Alert mechanisms
│   └── utils.py            # Utility functions
├── config/
│   ├── config.yaml         # Main configuration
│   ├── keywords.txt        # Keywords to monitor
│   └── onion_urls.txt      # URLs to crawl
├── archive/                # Raw HTML storage
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding Custom Features
1. **Custom Parsers**: Extend `ContentParser` class
2. **New Alert Methods**: Add methods to `AlertSystem`
3. **Additional Storage**: Implement storage backends
4. **Custom Crawlers**: Extend crawler for specific sites

### Testing
```bash
# Test individual components
python -c "from src.tor_crawler import TorCrawler; print('Import successful')"

# Test with sample data
python src/main.py --mode test
```

## 🐛 Troubleshooting

### Common Issues

#### Tor Connection Failed
```
Error: Tor connection test failed
```
**Solutions**:
- Ensure Tor is running on port 9050
- Check firewall settings
- Verify proxy configuration in `config.yaml`

#### MongoDB Connection Error
```
Failed to connect to MongoDB
```
**Solutions**:
- Start MongoDB service
- Check connection string in configuration
- Use file storage as fallback (automatic)

#### Import Errors
```
Import "telegram" could not be resolved
```
**Solutions**:
- Install missing dependencies: `pip install -r requirements.txt`
- Activate virtual environment
- Check Python version (3.10+ required)

#### Permission Errors
```
PermissionError: [Errno 13] Permission denied
```
**Solutions**:
- Run with appropriate permissions
- Check directory write permissions
- Use `--user` flag for pip installations

### Debug Mode
```bash
python src/main.py --verbose --mode test
```

## 📈 Performance Optimization

### Crawler Optimization
- Adjust `delay_between_requests` for your use case
- Limit `max_pages_per_site` to avoid overloading
- Use `AsyncTorCrawler` for better performance

### Database Optimization
- Create indexes on frequently queried fields
- Regular cleanup of old findings
- Consider database partitioning for large datasets

### Resource Management
- Monitor memory usage during crawling
- Implement log rotation
- Clean up archived files periodically

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚖️ Legal Notice

**IMPORTANT**: This tool is for educational and research purposes only. Users must:

- Comply with all applicable laws and regulations
- Obtain proper authorization before monitoring
- Respect privacy and intellectual property rights
- Use the tool responsibly and ethically

The authors are not responsible for any illegal use of this software.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review configuration examples
3. Enable verbose logging for debugging
4. Create an issue with detailed information

## 🔄 Updates & Maintenance

### Regular Maintenance
- Update dependencies regularly
- Monitor for security advisories
- Clean up old data and logs
- Review and update configurations

### Version History
- **v1.0.0**: Initial release with core features

---

**Remember**: Always use this tool responsibly and in accordance with applicable laws and regulations. The dark web contains illegal content, and accessing such content may be illegal in your jurisdiction.