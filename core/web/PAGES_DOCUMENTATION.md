# Pages Documentation

## Layout System

All pages use a consistent layout template provided by the `Layout` component:

### Layout Component (`src/components/Layout.tsx`)

The Layout provides:
- **Header** with navigation and theme toggle
- **Main content area** with proper spacing
- **Footer** with branding
- **Consistent background** (gradient-cyber)
- **Scanline effect** overlay

**Usage:**
```tsx
import { Layout } from "@/components/Layout";

export default function YourPage() {
  return (
    <Layout>
      {/* Your page content */}
    </Layout>
  );
}
```

## Pages

### 1. Home Page (`/`)
**Component:** `src/pages/Index.tsx`

**Features:**
- Live news feed with all articles
- Sidebar filters (Categories & Smart Groups)
- Search functionality
- Sort options (Latest, Oldest, Source)
- Recent filter (Last 24 hours)
- Infinite scroll capability

**Data Source:** Fetches from `/data/news_recent.json`

### 2. Morning Call (`/morning-call`)
**Component:** `src/pages/MorningCall.tsx`

**Features:**
- Daily security news digest
- Stats cards showing:
  - Curated stories count
  - Critical vulnerabilities count
  - Trending topics count
- **Trending Topics** section (Last 24h with counts)
- **Critical Vulnerabilities** section
- **Today's Curated Highlights** section

**Data Filtering:**
- Shows only items from last 24 hours
- Prioritizes curated content
- Highlights critical vulnerabilities

**Perfect for:** Daily security briefings and morning team calls

### 3. Archive (`/archive`)
**Component:** `src/pages/Archive.tsx`

**Features:**
- Historical news organized by month
- Expandable/collapsible month sections
- "Expand All" / "Collapse All" buttons
- Statistics:
  - Total articles
  - Months covered
- Chronological organization (newest first)

**Data Grouping:**
- Groups articles by month (e.g., "December 2025")
- Sorts months in descending order
- Shows article count per month

**Perfect for:** Browsing historical news, research, reference

### 4. Trends (`/trends`)
**Component:** `src/pages/Trends.tsx`

**Features:**
- Analytics and trend visualization
- Timeframe selector (7 days / 30 days)
- **Stats Overview:**
  - Total articles
  - Curated count
  - Average per day
  - Active categories
- **Activity Timeline:**
  - Bar chart showing daily article counts
  - Visual representation of news volume
- **Top Categories:**
  - Ranked by article count
  - Percentage bars
- **Top Sources:**
  - Most active news sources
  - Percentage distribution
- **Trending Topics:**
  - Most mentioned smart groups
  - Bubble display with counts

**Data Analysis:**
- Filters by selected timeframe
- Calculates percentages
- Sorts by frequency
- Visual progress bars

**Perfect for:** Understanding security landscape, identifying hot topics, source analysis

## Navigation

All pages are accessible via the header navigation:
- **k5.ai Logo** → Home
- **Morning Call** → `/morning-call`
- **Archive** → `/archive`
- **Trends** → `/trends`

Active page is highlighted in primary color.

## Shared Components

### NewsCard
Used across all pages to display individual news items consistently.

**Features:**
- Source badge
- Category badge (color-coded)
- Title with external link
- Summary (line-clamped to 3 lines)
- Smart group tags
- Timestamp
- Hover effects

### Data Loading States
All pages implement:
- **Loading state:** Spinner with loading message
- **Error state:** Error message with border
- **Empty state:** "No results" message

## Theme Support

All pages fully support:
- ✅ Dark theme (default)
- ✅ Light theme (via toggle button)
- ✅ System preference detection
- ✅ Persistent preference (localStorage)

## Responsive Design

All pages are responsive:
- **Mobile:** Stacked layout, simplified navigation
- **Tablet:** Adaptive grid layouts
- **Desktop:** Full multi-column layouts

## SEO

Each page includes:
- Unique page title
- Meta description
- Proper semantic HTML
- Helmet for dynamic meta tags

## Data Flow

```
news_recent.json
    ↓
fetchNewsData()
    ↓
Page Components (useState)
    ↓
Data Processing (useMemo)
    ↓
Render Components
```

All pages use the same data source but filter/process it differently based on their purpose.

## Adding New Pages

To add a new page:

1. **Create page component:**
   ```tsx
   // src/pages/YourPage.tsx
   import { Layout } from "@/components/Layout";
   import { Helmet } from "react-helmet-async";

   export default function YourPage() {
     return (
       <Layout>
         <Helmet>
           <title>Your Page — k5.ai</title>
           <meta name="description" content="..." />
         </Helmet>

         {/* Your content */}
       </Layout>
     );
   }
   ```

2. **Add route in App.tsx:**
   ```tsx
   import YourPage from "./pages/YourPage";
   // ...
   <Route path="/your-page" element={<YourPage />} />
   ```

3. **Add navigation link in Header.tsx:**
   ```tsx
   <Link to="/your-page">Your Page</Link>
   ```

## Styling Consistency

All pages follow these conventions:
- **Page title:** `text-3xl font-bold`
- **Section titles:** `text-xl font-semibold`
- **Cards:** `bg-card border-border rounded-lg p-5`
- **Stats:** Large numbers with icons
- **Spacing:** `space-y-6` for main sections
- **Colors:** Use CSS variables for theme compatibility

## Performance

- Data fetched once per page load
- `useMemo` for expensive computations
- Lazy rendering for long lists
- Optimized re-renders

## Future Enhancements

Potential additions:
- Export functionality (CSV, PDF)
- Date range picker
- Advanced filters
- Bookmarking/favorites
- Email digest subscriptions
- Custom dashboards
