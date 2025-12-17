#!/bin/bash
#
# DMI v0.1.10 Deployment Preparation Script
# Prepares static files for upload to any web host
#

set -e  # Exit on error

echo "=================================================="
echo "DMI v0.1.

 Deployment Preparation"
echo "=================================================="
echo ""

# Configuration
DEPLOY_DIR="deploy"
WEB_DIR="web"
DATA_DIR="data"
VERSION="0.1.10"

# Clean previous deployment
if [ -d "$DEPLOY_DIR" ]; then
    echo "🗑️  Removing previous deployment directory..."
    rm -rf "$DEPLOY_DIR"
fi

# Create deployment directory
echo "📁 Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"

# Copy web files
echo "📋 Copying web files..."
cp -r "$WEB_DIR"/* "$DEPLOY_DIR/"

# Remove symlink if exists
if [ -L "$DEPLOY_DIR/data" ]; then
    echo "🔗 Removing symlink..."
    rm "$DEPLOY_DIR/data"
fi

# Copy actual data files (not symlink)
echo "📊 Copying data files..."
cp -r "$DATA_DIR" "$DEPLOY_DIR/data"

# Generate health.json
echo "🏥 Generating health.json..."
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Find latest period from time series
if [ -f "$DEPLOY_DIR/data/outputs/published/dmi_timeseries_2010_2024.json" ]; then
    # Use jq if available, otherwise parse with grep/sed
    if command -v jq &> /dev/null; then
        LATEST_PERIOD=$(jq -r '.end_period' "$DEPLOY_DIR/data/outputs/published/dmi_timeseries_2010_2024.json")
        OBS_COUNT=$(jq -r '.observations_count' "$DEPLOY_DIR/data/outputs/published/dmi_timeseries_2010_2024.json")
    else
        LATEST_PERIOD=$(grep -o '"end_period": *"[^"]*"' "$DEPLOY_DIR/data/outputs/published/dmi_timeseries_2010_2024.json" | sed 's/.*"\([^"]*\)"/\1/')
        OBS_COUNT=$(grep -o '"observations_count": *[0-9]*' "$DEPLOY_DIR/data/outputs/published/dmi_timeseries_2010_2024.json" | sed 's/.*: *//')
    fi
else
    LATEST_PERIOD="2024-11"
    OBS_COUNT="835"
fi

cat > "$DEPLOY_DIR/health.json" << EOF
{
  "status": "healthy",
  "version": "$VERSION",
  "build_timestamp": "$BUILD_TIME",
  "git_sha": "$GIT_SHA",
  "latest_period": "$LATEST_PERIOD",
  "data_vintage": "2023",
  "observations_count": $OBS_COUNT,
  "last_updated": "$(date -u +"%Y-%m-%d")",
  "endpoints": {
    "dashboard": "/",
    "timeseries": "/data/outputs/published/dmi_timeseries_2010_2024.json",
    "latest": "/data/outputs/dmi_release_$LATEST_PERIOD.json",
    "latest_with_ci": "/data/outputs/dmi_release_${LATEST_PERIOD}_with_ci.json",
    "latest_u6": "/data/outputs/dmi_release_${LATEST_PERIOD}_u6.json",
    "latest_core": "/data/outputs/dmi_release_${LATEST_PERIOD}_core.json"
  }
}
EOF

# Generate metadata.json
echo "📋 Generating metadata.json..."
cat > "$DEPLOY_DIR/metadata.json" << EOF
{
  "dataset_name": "Distributional Misery Index",
  "version": "$VERSION",
  "license": "MIT",
  "contact": "https://github.com/tcwilliams79/dmi",
  "website": "https://dmianalysis.org",
  "citation": "Williams, T.C. (2024). Distributional Misery Index v$VERSION",
  "data_vintage": "2023",
  "coverage": {
    "start_period": "2011-01",
    "end_period": "$LATEST_PERIOD",
    "frequency": "monthly",
    "geographic_level": "national",
    "income_groups": 5
  },
  "files": {
    "timeseries": "/data/outputs/published/dmi_timeseries_2010_2024.json",
    "latest": "/data/outputs/dmi_release_$LATEST_PERIOD.json",
    "schema": "/schemas/dmi_output_schema.json",
    "health": "/health.json"
  },
  "build": {
    "timestamp": "$BUILD_TIME",
    "git_sha": "$GIT_SHA"
  }
}
EOF

# Create .htaccess for production optimization
echo "⚙️  Creating .htaccess file..."
cat > "$DEPLOY_DIR/.htaccess" << 'EOF'
# DMI Dashboard - Production Configuration

# Enable compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript application/json
</IfModule>

# Browser caching
<IfModule mod_expires.c>
    ExpiresActive On
    
    # HTML - short cache (pages may update)
    ExpiresByType text/html "access plus 1 hour"
    
    # Data files - short cache (updates monthly)
    ExpiresByType application/json "access plus 1 day"
    
    # CSS and JavaScript - longer cache
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
    
    # Images
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
</IfModule>

# Security headers
<IfModule mod_headers.c>
    # Prevent clickjacking
    Header always set X-Frame-Options "SAMEORIGIN"
    
    # XSS protection
    Header always set X-XSS-Protection "1; mode=block"
    
    # Prevent MIME sniffing
    Header always set X-Content-Type-Options "nosniff"
    
    # CORS for data files (if needed)
    <FilesMatch "\.(json)$">
        Header set Access-Control-Allow-Origin "*"
    </FilesMatch>
</IfModule>

# Custom error pages (optional)
# ErrorDocument 404 /404.html

# Disable directory browsing
Options -Indexes

# Force HTTPS (uncomment if SSL is configured)
# RewriteEngine On
# RewriteCond %{HTTPS} off
# RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
EOF

# Create README for deployment
echo "📝 Creating deployment README..."
cat > "$DEPLOY_DIR/DEPLOYMENT_README.txt" << 'EOF'
DMI v0.1.10 - Deployment Instructions
======================================

UNIVERSAL DEPLOYMENT (Works on Any Web Host):

Step 1: Prepare
----------------
You have this deploy/ directory ready to upload.

Step 2: Upload Files
--------------------
Choose one method:

A) Via FTP/SFTP:
   - Connect to your host
   - Navigate to web root (e.g., public_html/)
   - Upload all contents of this deploy/ folder
   
B) Via File Manager:
   - Log into your hosting control panel
   - Open File Manager
   - Navigate to web root
   - Upload dmi-v0.1.10-deployment.zip
   - Extract the .zip file
   - Delete the .zip after extraction

Step 3: Verify Permissions
--------------------------
- Files should be 644 (rw-r--r--)
- Directories should be 755 (rwxr-xr-x)
- Most hosts set this automatically

Step 4: Test
------------
Visit https://yourdomain.com/path/ and verify:
- Dashboard loads
- Charts render
- health.json returns 200
- No console errors (F12)

PLATFORM-SPECIFIC NOTES:

cPanel (HostGator, Bluehost, SiteGround, etc.):
- Web root: public_html/
- Subdirectory: public_html/dashboard/
- File Manager: Built into cPanel
- .htaccess: Fully supported

Plesk:
- Web root: httpdocs/
- .htaccess: Fully supported

Nginx:
- .htaccess: NOT supported (ignored)
- Dashboard still works, just missing caching optimizations

FILES INCLUDED:
- index.html (dashboard)
- health.json (status endpoint)
- metadata.json (dataset info)
- data/ (all DMI data)
- .htaccess (Apache optimization)

REQUIREMENTS:
- Static file serving only
- No server-side code needed
- No database required
- Works on ANY web host

For detailed instructions, see:
docs/DEPLOYMENT_GUIDE.md in the repository

Support: https://github.com/tcwilliams79/dmi
EOF

# Create file list
echo "📄 Generating file manifest..."
find "$DEPLOY_DIR" -type f -o -type d | sort > "$DEPLOY_DIR/FILE_MANIFEST.txt"

# Calculate total size
echo ""
echo "📊 Deployment Statistics:"
echo "------------------------"
TOTAL_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l | tr -d ' ')
echo "Total size: $TOTAL_SIZE"
echo "Total files: $FILE_COUNT"
echo "Version: $VERSION"
echo "Latest period: $LATEST_PERIOD"
echo ""

# Create compressed archive for easy upload
echo "📦 Creating deployment archive..."
cd "$DEPLOY_DIR"
zip -r ../dmi-v$VERSION-deployment.zip . > /dev/null 2>&1
cd ..
ARCHIVE_SIZE=$(du -sh dmi-v$VERSION-deployment.zip | cut -f1)
echo "✅ Archive created: dmi-v$VERSION-deployment.zip ($ARCHIVE_SIZE)"

echo ""
echo "=================================================="
echo "✅ Deployment preparation complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Upload 'deploy/' directory contents to your web server"
echo "2. Or upload 'dmi-v$VERSION-deployment.zip' and extract on server"
echo "3. Access your dashboard at: https://yourdomain.com/path/"
echo "4. Verify health: https://yourdomain.com/path/health.json"
echo ""
echo "See deploy/DEPLOYMENT_README.txt for detailed instructions"
echo ""
