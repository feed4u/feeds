# React App Migration to Static JSON Data

## Summary

The React application has been updated to fetch news data from a static JSON file (`/data/news_recent.json`) instead of using hardcoded mock data. This enables deployment to Cloudflare Pages without requiring a backend server.

## Changes Made

### 1. Data Fetching (`src/data/newsData.ts`)

- **Added**: `fetchNewsData()` function to fetch from `/data/news_recent.json`
- **Added**: Type definitions for the API response (`NewsDataResponse`, `RawNewsItem`)
- **Added**: `toNewsItem()` to convert backend data format to frontend format
- **Added**: `TYPE_TO_CATEGORY_MAP` to map backend type names to frontend category IDs
- **Removed**: Hardcoded mock data

**Key Transformations:**
- `type` → `category` (with mapping)
- `smart_groups` → `smartGroups`
- `published_ts` → `date` (converted to JavaScript Date)
- `link` → `url`
- Added unique `id` generation from timestamp + index

### 2. NewsFeed Component (`src/components/NewsFeed.tsx`)

- **Added**: `useState` for `newsItems`, `loading`, and `error` states
- **Added**: `useEffect` to fetch data on component mount
- **Added**: Loading spinner UI
- **Added**: Error message UI
- **Updated**: "curated" filter to check `item.curated` boolean
- **Changed**: `newsItems` from import to state variable

### 3. Sidebar Component (`src/components/Sidebar.tsx`)

- **Added**: `newsItems` prop to receive data from parent
- **Added**: `useMemo` hooks to dynamically generate categories and smart groups
- **Added**: `CATEGORY_LABELS` mapping for display names
- **Removed**: Dependency on static imports
- **Changed**: Categories and smart groups now generated from actual data with live counts

**Category Generation:**
- "All" shows total count
- "Curated" shows count of curated items
- Other categories sorted by count (descending)

**Smart Group Generation:**
- Extracts all smart groups from news items
- Counts occurrences
- Shows top 20 by count (descending)

### 4. NewsCard Component (`src/components/NewsCard.tsx`)

- **Added**: `CATEGORY_LABELS` mapping for proper category display
- **Updated**: Category color variants to include malware, leaks, crypto
- **Fixed**: Smart group display to show actual group names (not modified)
- **Changed**: Category display from `category.replace('-', ' ')` to proper label lookup

### 5. Public Data Access

- **Created**: Symlink from `/data` to `public/data`
- This makes the JSON file accessible at `/data/news_recent.json` in the deployed app

### 6. Documentation

- **Created**: `CLOUDFLARE_DEPLOY.md` with deployment instructions
- **Created**: `CHANGES.md` (this file) documenting all modifications

## Data Flow

1. **Build Time**: Python script generates `/data/news_recent.json`
2. **App Load**: React app fetches from `/data/news_recent.json`
3. **Transform**: Data transformed from backend to frontend format
4. **Display**: Components render with live data
5. **Filter**: User interactions filter the fetched data

## Deployment Ready

The app is now fully static and can be deployed to:
- ✅ Cloudflare Pages
- ✅ Vercel
- ✅ Netlify
- ✅ Any static hosting platform

## Testing Locally

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 and verify:
1. News items load from JSON
2. Categories show correct counts
3. Smart groups show correct counts
4. Filtering works (categories, smart groups, search)
5. "Curated" filter shows only curated items

## Data Update Workflow

1. Run Python script: `python scripts/build_news_json.py`
2. JSON updated: `/data/news_recent.json`
3. Rebuild React app: `npm run build`
4. Deploy: `wrangler pages deploy dist`

Or set up automated deployment with GitHub Actions.
