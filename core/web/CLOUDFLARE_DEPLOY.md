# Deploying to Cloudflare Pages

This React application is a static site that displays security news data from JSON files, making it perfect for Cloudflare Pages deployment.

## Quick Start Guide

### Step 1: Generate Fresh Data

From the project root, run the complete pipeline:

```bash
cd /Users/perttu/study/k5-security-news

# Run the pipeline (fetches news, builds archives, generates trends, syncs data)
./scripts/run_pipeline.sh

# OR with daily report (requires OPENAI_API_KEY)
export OPENAI_API_KEY='your-key-here'
./scripts/run_full_pipeline.sh --with-report
```

This will:
- Fetch news from RSS feeds → `data/news_recent.json`
- Build archives → `data/archive/`
- Generate trends → `data/trends.json`
- Sync everything to `web/public/data/`

### Step 2: Build the Web App

```bash
cd web
npm install  # First time only
npm run build
```

This creates a `dist/` folder with your production-ready static site.

### Step 3: Preview Locally (Optional)

```bash
npm run preview
# Visit http://localhost:4173
```

## Local Development

To develop the UI with hot-reload:

```bash
cd web
npm run dev
# Visit http://localhost:5173
```

## Cloudflare Pages Deployment

### Option 1: Direct Upload (Fastest)

This is the quickest way to get your site live:

```bash
# 1. Navigate to web directory
cd web

# 2. Install Wrangler CLI (first time only)
npm install -g wrangler

# 3. Login to Cloudflare
wrangler login

# 4. Deploy the dist folder
wrangler pages deploy dist --project-name=k5-security-news
```

After deployment, you'll get a URL like: `https://k5-security-news.pages.dev`

**To update the site:**
```bash
# 1. Update data (from project root)
cd /Users/perttu/study/k5-security-news
./scripts/run_pipeline.sh

# 2. Rebuild and deploy
cd web
npm run build
wrangler pages deploy dist
```

### Option 2: Git Integration (For Continuous Deployment)

Set up automatic deployments when you push to GitHub:

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/k5-security-news.git
   git push -u origin main
   ```

2. **Connect to Cloudflare Pages:**
   - Go to [Cloudflare Pages Dashboard](https://dash.cloudflare.com/pages)
   - Click "Create a project"
   - Click "Connect to Git"
   - Select your `k5-security-news` repository

3. **Configure build settings:**
   - **Project name**: `k5-security-news` (or your choice)
   - **Production branch**: `main`
   - **Framework preset**: `Vite`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Root directory**: `web`

4. **Click "Save and Deploy"**

Cloudflare will automatically deploy whenever you push to the main branch.

**Important:** You need to commit the `web/public/data/` folder to git for this to work, or set up GitHub Actions to run the pipeline before deploying.

## Updating Data & Redeploying

### Manual Updates

```bash
# 1. Run the pipeline to get fresh data
cd /Users/perttu/study/k5-security-news
./scripts/run_pipeline.sh

# 2. Build and deploy
cd web
npm run build
wrangler pages deploy dist
```

### Scheduled Updates (Recommended)

Set up a cron job to automatically update your data:

```bash
# Edit crontab
crontab -e

# Add this line to run every 6 hours
0 */6 * * * cd /Users/perttu/study/k5-security-news && ./scripts/run_pipeline.sh >> logs/pipeline.log 2>&1
```

Then manually deploy when needed, or automate with:

```bash
# Create update and deploy script
cat > scripts/update_and_deploy.sh << 'EOF'
#!/bin/bash
cd /Users/perttu/study/k5-security-news

# Run pipeline
./scripts/run_pipeline.sh

# Build and deploy
cd web
npm run build
wrangler pages deploy dist --project-name=k5-security-news

echo "Deployment complete: $(date)"
EOF

chmod +x scripts/update_and_deploy.sh
```

### GitHub Actions (Advanced)

Create `.github/workflows/deploy.yml`:

```yaml
name: Update and Deploy

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r scripts/requirements.txt

      - name: Run pipeline
        run: ./scripts/run_pipeline.sh

      - name: Build web app
        run: |
          cd web
          npm ci
          npm run build

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: k5-security-news
          directory: web/dist
```

## Troubleshooting

### Data Not Loading

**Issue:** News feed shows "Loading..." forever or displays errors

**Solutions:**
1. Check browser console (F12) for errors
2. Verify `web/public/data/` contains JSON files:
   ```bash
   ls -lh web/public/data/
   # Should see: news_recent.json, trends.json, category_metadata.json
   ```
3. Ensure data is synced:
   ```bash
   ./scripts/sync_web_data.sh
   ```
4. Validate JSON files:
   ```bash
   jq . web/public/data/news_recent.json > /dev/null && echo "Valid JSON"
   ```

### Build Fails

**Issue:** `npm run build` fails

**Solutions:**
1. Clean and reinstall dependencies:
   ```bash
   cd web
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```
2. Check for TypeScript errors:
   ```bash
   npm run build 2>&1 | grep "error"
   ```
3. Ensure you're using compatible Node version:
   ```bash
   node --version  # Should be 18.x or higher
   ```

### Routes Return 404

**Issue:** Direct navigation to `/trends` or `/archive` returns 404

**Solution:** Cloudflare Pages automatically handles SPA routing. If issues persist:

1. Create `web/public/_redirects`:
   ```
   /*    /index.html   200
   ```
2. Rebuild and redeploy

### Deployment Fails with Wrangler

**Issue:** `wrangler pages deploy` fails

**Solutions:**
1. Ensure you're logged in:
   ```bash
   wrangler whoami
   wrangler login  # If not logged in
   ```
2. Check project name:
   ```bash
   wrangler pages project list
   ```
3. Try with full command:
   ```bash
   wrangler pages deploy dist --project-name=your-project-name --branch=main
   ```

## Site Performance

Your deployed site should achieve:
- **Lighthouse Score:** 95+ (Performance, Accessibility, Best Practices, SEO)
- **Load Time:** < 2 seconds (global average)
- **Bandwidth:** ~500KB initial load (including data)

Cloudflare Pages provides:
- Global CDN (300+ cities)
- Automatic SSL/TLS
- HTTP/3 support
- Automatic compression (Brotli/Gzip)
- DDoS protection

## Summary

**Simplest deployment workflow:**

```bash
# 1. Generate data
./scripts/run_pipeline.sh

# 2. Build
cd web && npm run build

# 3. Deploy
wrangler pages deploy dist --project-name=k5-security-news
```

**Your site will be live at:** `https://k5-security-news.pages.dev`

**To update:** Just repeat the 3 steps above!

## Support

- **Cloudflare Pages Docs:** https://developers.cloudflare.com/pages/
- **Wrangler CLI Docs:** https://developers.cloudflare.com/workers/wrangler/
- **Vite Docs:** https://vitejs.dev/guide/

For project-specific issues, see [PIPELINE.md](../PIPELINE.md) and [CLAUDE.md](../CLAUDE.md)
