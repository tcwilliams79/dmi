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
